"""Menulux portalı satış raporu istemcisi.

Menulux resmi bir API anahtarı vermiyor; portalın kendi web arayüzünün kullandığı uç noktalar kullanılır:
  1) GET  portal.menulux.com/Configuration/GeneratePublicKey          -> {"PublicKey": ...}
  2) POST menuluxportalapi.azurewebsites.net/api/UserAPI/LoginUser    (başlık: Publickey) -> yanıt başlığında AuthKey
  3) Sonraki isteklerde başlıklar: AuthKey, CustomerID.
Kullanıcı adı / şifre koda yazılmaz; ortam değişkenleri: MENULUX_USER, MENULUX_PASS, (ops.) MENULUX_CUSTOMER_ID (varsayılan 14596).
"""
import datetime
import difflib
import json
import logging
import os
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor

import requests
from django.utils import timezone

log = logging.getLogger(__name__)

PORTAL = 'https://portal.menulux.com'
API = 'https://menuluxportalapi.azurewebsites.net'
ZAMAN_ASIMI = 25
HAVUZ_BOYUTU = 24   # coklu()'daki paralel işçi sayısıyla uyumlu olsun diye (bkz. aşağıdaki HAVUZ_ISCI)
HAVUZ_ISCI = 24
_kilit = threading.Lock()
_yerel = threading.local()   # thread havuzundaki işçiler veritabanına dokunmasın diye işaret
_oturum = {'authkey': None, 'zaman': 0.0}
OTURUM_OMRU = 25 * 60   # sn; süre dolmadan yenilenir, 401/403'te de yeniden girilir


def _oturum_al():
    """Tüm _get() çağrılarının paylaştığı, bağlantı havuzlu (keep-alive) requests.Session.
    Önceden her _get() çağrısı ayrı bir TCP+TLS bağlantısı açıyordu (requests.get modül fonksiyonu);
    tek sayfa açılışında 20-30 paralel isteğin her biri yeni bağlantı kurduğundan bu, gerçek
    Menulux gecikmesinin üzerine ciddi ekstra süre (her bağlantı için TLS el sıkışması) biniyordu.
    Paylaşılan Session + yeterince büyük bağlantı havuzu, aynı anda çalışan thread'lerin bağlantıyı
    yeniden kullanmasını sağlar."""
    s = getattr(_oturum_al, '_s', None)
    if s is None:
        s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=HAVUZ_BOYUTU, pool_maxsize=HAVUZ_BOYUTU, max_retries=0)
        s.mount('https://', adapter)
        s.mount('http://', adapter)
        _oturum_al._s = s
    return s


class MenuluxHata(Exception):
    """Kullanıcıya gösterilebilir (şifre içermeyen) hata."""


def ayar():
    kul, sif = os.environ.get('MENULUX_USER', '').strip(), os.environ.get('MENULUX_PASS', '')
    if not kul or not sif:
        return None
    return {'kullanici': kul, 'sifre': sif, 'ana': int(os.environ.get('MENULUX_CUSTOMER_ID', '14596') or 14596)}


def ayarli_mi():
    return ayar() is not None


def _ana():
    a = ayar()
    if not a:
        raise MenuluxHata('Menulux bağlantı bilgileri (MENULUX_USER / MENULUX_PASS) sunucuda tanımlı değil.')
    return a


TARAYICI = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/130.0.0.0 Safari/537.36')


def _parca(r, n=70):
    """Şifre/anahtar içermeyen, yanıtın başından kısa bir teşhis parçası."""
    try:
        t = ' '.join((r.text or '')[:n].split())
    except Exception:
        t = ''
    return 'HTTP %s%s' % (r.status_code, (': ' + t) if t else '')


def _giris(a):
    t0 = time.monotonic()
    s = _oturum_al()
    s.headers.update({'User-Agent': TARAYICI, 'Accept-Language': 'tr-TR,tr;q=0.9'})
    try:
        s.get(PORTAL + '/Account/Login', timeout=ZAMAN_ASIMI)      # tarayıcı gibi: önce giriş sayfası (oturum çerezi)
        r = s.get(PORTAL + '/Configuration/GeneratePublicKey', timeout=ZAMAN_ASIMI,
                  headers={'X-Requested-With': 'XMLHttpRequest', 'Referer': PORTAL + '/Account/Login', 'Accept': 'application/json, text/javascript, */*'})
    except requests.RequestException as e:
        raise MenuluxHata('Menulux\'a ulaşılamadı (%s).' % e.__class__.__name__)
    try:
        pk = r.json().get('PublicKey')
    except ValueError:
        raise MenuluxHata('Menulux giriş anahtarı okunamadı (%s).' % _parca(r))
    if not pk:
        raise MenuluxHata('Menulux giriş anahtarı boş geldi (%s).' % _parca(r))
    try:
        r = s.post(API + '/api/UserAPI/LoginUser', timeout=ZAMAN_ASIMI,
                   json={'UserName': a['kullanici'], 'Password': a['sifre'], 'UserLog': True, 'OTPCode': None, 'UserID': None},
                   headers={'Publickey': pk, 'Origin': PORTAL, 'Referer': PORTAL + '/'})
    except requests.RequestException as e:
        raise MenuluxHata('Menulux\'a ulaşılamadı (%s).' % e.__class__.__name__)
    if r.status_code == 202:
        raise MenuluxHata('Menulux hesabı SMS doğrulaması istiyor; otomatik giriş yapılamaz.')
    if r.status_code != 200:
        raise MenuluxHata('Menulux girişi reddedildi (%s). Kullanıcı adı/şifreyi kontrol edin.' % _parca(r, 50))
    ak = r.headers.get('AuthKey')
    if not ak:
        raise MenuluxHata('Menulux giriş yanıtında oturum anahtarı yok.')
    log.info('Menulux girişi %.2fsn sürdü', time.monotonic() - t0)
    return ak


def _authkey(yenile=False):
    """Oturum anahtarı: önce bellekte, sonra (diğer gunicorn işçileriyle paylaşılan) veritabanında, yoksa yeni giriş."""
    havuz = getattr(_yerel, 'havuz', False)
    with _kilit:
        simdi = timezone.now().timestamp()
        if not yenile and _oturum['authkey'] and simdi - _oturum['zaman'] <= OTURUM_OMRU:
            return _oturum['authkey']
        if not yenile and not havuz:
            var, veri = _oku('authkey', datetime.timedelta(seconds=OTURUM_OMRU))
            if var and veri.get('k'):
                _oturum['authkey'], _oturum['zaman'] = veri['k'], simdi
                return veri['k']
        _oturum['authkey'] = _giris(_ana())
        _oturum['zaman'] = simdi
        if not havuz:
            _yaz('authkey', {'k': _oturum['authkey']})
        return _oturum['authkey']


def oturumu_sifirla():
    with _kilit:
        _oturum['authkey'] = None
        _oturum['zaman'] = 0.0
        _oturum_al._s = None


def _get(yol, **params):
    a = _ana()
    t0 = time.monotonic()
    for deneme in (0, 1):
        ak = _authkey(yenile=bool(deneme))
        try:
            r = _oturum_al().get(API + '/api/' + yol, params=params, timeout=ZAMAN_ASIMI,
                                 headers={'AuthKey': ak, 'CustomerID': str(a['ana']), 'Origin': PORTAL, 'Referer': PORTAL + '/', 'User-Agent': TARAYICI,
                                          'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json'})
        except requests.RequestException as e:
            raise MenuluxHata('Menulux\'a ulaşılamadı (%s).' % e.__class__.__name__)
        if r.status_code in (401, 403) and deneme == 0:
            continue
        if r.status_code != 200:
            raise MenuluxHata('Menulux isteği başarısız (%s, %s).' % (_parca(r, 50), yol.split('?')[0]))
        try:
            veri = r.json()
        except ValueError:
            raise MenuluxHata('Menulux yanıtı okunamadı (%s, %s).' % (_parca(r, 50), yol))
        sure = time.monotonic() - t0
        if sure > 1.5:
            log.warning('Menulux yavaş yanıt: %s %.2fsn', yol.split('?')[0], sure)
        return veri
    raise MenuluxHata('Menulux oturumu açılamadı.')


def _t(d, bitis=False):
    return '%s%s' % (d.strftime('%Y-%m-%d'), 'T23:59:59.000Z' if bitis else 'T00:00:00.000Z')


# ------------------------------------------------------------------ önbellek
def _ttl(bit):
    return datetime.timedelta(hours=6) if bit < timezone.localdate() else datetime.timedelta(minutes=5)


def _oku(anahtar, ttl):
    from .models import MenuluxOnbellek
    kayit = MenuluxOnbellek.objects.filter(anahtar=anahtar).first()
    if kayit and timezone.now() - kayit.olusturma < ttl:
        return True, kayit.veri
    return False, None


def _yaz(anahtar, veri):
    from .models import MenuluxOnbellek
    try:
        MenuluxOnbellek.objects.update_or_create(anahtar=anahtar, defaults={'veri': veri, 'olusturma': timezone.now()})
    except Exception:
        log.exception('Menulux önbelleği yazılamadı')


def onbellekli(anahtar, ttl, fonksiyon):
    var, veri = _oku(anahtar, ttl)
    if var:
        return veri
    veri = fonksiyon()
    _yaz(anahtar, veri)
    return veri


def coklu(isler):
    """isler: [(anahtar, ttl, fonksiyon)]. Veritabanına yalnız bu (ana) thread dokunur; eksikler thread havuzunda
    yalnızca HTTP ile çekilir. Sonuçlar giriş sırasında döner."""
    t0 = time.monotonic()
    sonuc = [None] * len(isler)
    eksik = []
    for i, (anahtar, ttl, fn) in enumerate(isler):
        var, veri = _oku(anahtar, ttl)
        if var:
            sonuc[i] = veri
        else:
            eksik.append(i)
    if eksik:
        _authkey()          # oturumu ana thread'de aç/yükle; işçiler bellekteki anahtarı kullanır
        if len(eksik) == 1:
            cekilen = [isler[eksik[0]][2]()]
        else:
            def calis(i):
                _yerel.havuz = True
                try:
                    return isler[i][2]()
                finally:
                    _yerel.havuz = False
            with ThreadPoolExecutor(max_workers=min(HAVUZ_ISCI, len(eksik))) as ex:
                cekilen = list(ex.map(calis, eksik))
        for i, veri in zip(eksik, cekilen):
            sonuc[i] = veri
            _yaz(isler[i][0], veri)
    log.info('Menulux coklu(): %d iş (%d önbellekten, %d HTTP), %.2fsn',
             len(isler), len(isler) - len(eksik), len(eksik), time.monotonic() - t0)
    return sonuc


# ------------------------------------------------------------------ ham veri
def subeler_is():
    """subeler() ile aynı işi yapan (anahtar, ttl, fonksiyon) üçlüsü — coklu() içine karıştırılabilsin diye."""
    a = _ana()

    def al():
        veri = _get('CustomerAPI/GetSortedBranches', customerID=a['ana'], sortByRevenue='false')
        return [{'id': int(b['CustomerID']), 'ad': (b.get('Name') or '').strip()} for b in veri
                if b.get('CustomerID') and int(b['CustomerID']) != a['ana'] and not b.get('Deleted')]
    return ('subeler', datetime.timedelta(hours=1), al)


def subeler():
    """Menulux şubeleri: [{'id', 'ad'}] (merkez hariç, silinmişler hariç)."""
    return sorted(onbellekli(*subeler_is()), key=lambda b: b['ad'])


def ana_id():
    return _ana()['ana']


def ozet_is(cid, bas, bit):
    return ('ozet:%s:%s:%s' % (cid, bas, bit), _ttl(bit),
            lambda: _get('ReportAPI/GetEndOfDayReport', customerID=cid, startDate=_t(bas), endDate=_t(bit, True)))


def ozet(cid, bas, bit):
    return onbellekli(*ozet_is(cid, bas, bit))


def urun_is(cid, bas, bit, ana):
    def al():
        if cid == ana:
            veri = _get('ReportAPI/GetProductSalesReportDb', customerID=cid, startDate=_t(bas), endDate=_t(bit, True))
        else:
            veri = _get('ReportAPI/GetOrderSalesReportBranchesDb', customerID=cid, startDate=_t(bas), endDate=_t(bit, True))
        return veri if isinstance(veri, list) else []
    return ('urun:%s:%s:%s' % (cid, bas, bit), _ttl(bit), al)


def kategori_is(cid, bas, bit, ana):
    def al():
        if cid == ana:
            veri = _get('ReportAPI/GetCategorySalesReport', customerID=cid, startDate=_t(bas), endDate=_t(bit, True))
        else:
            tum = _get('ReportAPI/GetCategorySalesReportBranch', customerID=ana, startDate=_t(bas), endDate=_t(bit, True))
            veri = [x for x in (tum if isinstance(tum, list) else []) if x.get('CustomerID') == cid]
        return veri if isinstance(veri, list) else []
    return ('kategori:%s:%s:%s' % (cid, bas, bit), _ttl(bit), al)


def menu_is(cid):
    """Şubenin varsayılan menüsündeki ürünler (satılmayan ürün raporu için). rapor() bu işi ana coklu() dalgasına
    kattığından, burada oluşan bir hata tüm raporu düşürmesin diye yutulur (satılmayan listesi o şube için boş kalır)."""
    def al():
        try:
            menuler = _get('MenuAPI/GetMenusSummary', customerID=cid)
            menuler = menuler if isinstance(menuler, list) else []
            secili = next((m for m in menuler if m.get('Dafault')), menuler[0] if menuler else None)
            if not secili:
                return []
            veri = _get('OfferAPI/GetProducts', customerID=cid, menuID=secili['MenuID'])
            return veri if isinstance(veri, list) else []
        except MenuluxHata:
            log.warning('Menu çekilemedi (cid=%s)', cid)
            return []
    return ('menu:%s' % cid, datetime.timedelta(hours=6), al)


# ------------------------------------------------------------------ birleştirme
def _f(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


ODEME = [('CashPrice', 'Nakit'), ('CreditPrice', 'Kredi kartı'), ('OnlinePrice', 'Online'), ('TicketPrice', 'Yemek çeki'),
         ('SodexoCardPrice', 'Sodexo'), ('MultinetCardPrice', 'Multinet'), ('SetCardPrice', 'Setcard'),
         ('MetropolCardPrice', 'Metropol'), ('PayeCardPrice', 'Paye'), ('TokenFlexCardPrice', 'TokenFlex'),
         ('TurkuvazCardPrice', 'Türkuvaz'), ('AccountPrice', 'Cari hesap'), ('PersonalPrice', 'Personel'), ('CouponPrice', 'Kupon'),
         ('WalletPrice', 'Cüzdan'), ('TransferPrice', 'Havale'), ('ParacardPrice', 'Paracard')]


def ozet_sadelestir(o):
    o = o or {}
    odeme = [(ad, _f(o.get(k))) for k, ad in ODEME if _f(o.get(k))]
    return {
        'adisyon': int(_f(o.get('SessionCount'))), 'kisi': int(_f(o.get('GuestCount'))),
        'ciro': _f(o.get('SessionTotalPrice')), 'brut': _f(o.get('SessionOrderPrice')),
        'indirim': _f(o.get('SessionTotalDiscount')), 'ikram': _f(o.get('GiftedPrice')),
        'iptal': _f(o.get('CancelledPrice')), 'iade': _f(o.get('ReturnedPrice')),
        'kdv': _f(o.get('SessionTaxPrice')), 'urun_adedi': _f(o.get('ItemCount')),
        'paket': _f(o.get('SessionPackagePrice')), 'masa': _f(o.get('SessionTablePrice')), 'odeme': odeme,
    }


def ozetleri_topla(liste):
    t = {k: 0 for k in ('adisyon', 'kisi', 'ciro', 'brut', 'indirim', 'ikram', 'iptal', 'iade', 'kdv', 'urun_adedi', 'paket', 'masa')}
    odeme = {}
    for o in liste:
        for k in t:
            t[k] += o[k]
        for ad, v in o['odeme']:
            odeme[ad] = odeme.get(ad, 0) + v
    t['odeme'] = sorted(odeme.items(), key=lambda x: -x[1])
    return t


def ortalama(o):
    return o['ciro'] / o['adisyon'] if o['adisyon'] else 0.0


def _ad_anahtar(s):
    s = unicodedata.normalize('NFKD', (s or '').lower().replace('ı', 'i')).encode('ascii', 'ignore').decode()
    return ' '.join(s.split())


def urunleri_birlestir(satir_listeleri):
    """Birden çok şubenin ürün satırlarını ürün bazında toplar; satış satırı olmayanlar (ikram/iade/iptal) atlanır."""
    toplam = {}
    for satirlar in satir_listeleri:
        for r in satirlar:
            if r.get('Gifted') or r.get('Returned') or r.get('Cancelled'):
                continue
            anahtar = r.get('ProductID') or _ad_anahtar(r.get('Name'))
            u = toplam.setdefault(anahtar, {'ad': (r.get('Name') or '').strip(), 'kod': r.get('Code') or '',
                                            'grup': (r.get('GroupName') or '').strip(), 'adet': 0.0, 'tutar': 0.0, 'kdv': 0.0})
            u['adet'] += _f(r.get('Quantity')); u['tutar'] += _f(r.get('TotalPrice')); u['kdv'] += _f(r.get('TaxPrice'))
    return sorted(toplam.values(), key=lambda u: (-u['adet'], u['ad']))


def kategorileri_birlestir(satir_listeleri):
    toplam = {}
    for satirlar in satir_listeleri:
        for r in satirlar:
            k = toplam.setdefault(r.get('GroupID') or _ad_anahtar(r.get('Name')),
                                  {'ad': (r.get('Name') or '').strip(), 'adet': 0.0, 'net': 0.0, 'kdv': 0.0, 'tutar': 0.0})
            k['adet'] += _f(r.get('Quantity')); k['net'] += _f(r.get('NetPrice')); k['kdv'] += _f(r.get('TaxPrice')); k['tutar'] += _f(r.get('TotalPrice'))
    return sorted(toplam.values(), key=lambda k: -k['tutar'])


def _satilmayanlar_isle(menu_listeleri, satilan_urunler):
    """satilmayanlar()'ın HTTP'siz kısmı: zaten çekilmiş menü listelerinden hesaplar (rapor() tek dalgada besler)."""
    kodlar = {u['kod'] for u in satilan_urunler if u['kod']}
    adlar = {_ad_anahtar(u['ad']) for u in satilan_urunler}
    gorulen, sonuc = set(), []
    for menu in menu_listeleri:
        for p in menu:
            ad = (p.get('Name') or p.get('ProductName') or '').strip()
            kod = str(p.get('Code') or '')
            if not ad or (kod and kod in kodlar) or _ad_anahtar(ad) in adlar:
                continue
            anahtar = kod or _ad_anahtar(ad)
            if anahtar in gorulen:
                continue
            gorulen.add(anahtar)
            sonuc.append({'ad': ad, 'kod': kod, 'grup': (p.get('GroupName') or p.get('MenuGroupName') or '').strip(),
                          'fiyat': _f(p.get('Price'))})
    return sorted(sonuc, key=lambda x: (x['grup'], x['ad']))


def satilmayanlar(idler, satilan_urunler):
    """Menüde olup aralıkta hiç satılmayan ürünler. Eşleşme: ürün kodu, olmazsa ad. (rapor() dışından tek başına
    kullanım için; rapor() kendi menü işlerini ana coklu() dalgasına katıp _satilmayanlar_isle()'ı doğrudan çağırır.)"""
    return _satilmayanlar_isle(coklu([menu_is(c) for c in idler]), satilan_urunler)


def gunluk(idler, bas, bit, ana):
    """Gün gün ciro/adisyon (en fazla 62 gün)."""
    gunler = [bas + datetime.timedelta(days=i) for i in range((min(bit, bas + datetime.timedelta(days=61)) - bas).days + 1)]
    ids = [ana_id()] if ana else list(idler)
    ham = coklu([ozet_is(c, g, g) for g in gunler for c in ids])
    sonuc = []
    for i, g in enumerate(gunler):
        parca = [ozet_sadelestir(o) for o in ham[i * len(ids):(i + 1) * len(ids)]]
        sonuc.append((g, ozetleri_topla(parca)))
    return sonuc


def rapor(kapsam, bas, bit, urunler=True):
    """kapsam: 'tum' (merkez toplamı) ya da şube numaraları listesi. Tek sözlükte tüm rapor verisi.

    Performans: önceden özet/kırılım/kategori/ürün + günlük döküm + menü (satılmayan ürün) ayrı ayrı
    coklu() dalgaları olarak sıralı çekiliyordu (sayfa açılışı ~10 sn sürüyordu). Artık tüm Menulux
    istekleri TEK coklu() çağrısında (tek thread havuzu dalgasında, paralel) toplanıyor."""
    ana = kapsam == 'tum'
    ana_no = ana_id()
    idler = [ana_no] if ana else list(kapsam)
    adlar = {b['id']: b['ad'] for b in subeler()}
    sube_ids = list(adlar) if ana else idler
    kirilim_ids = sube_ids if (ana or len(idler) > 1) else []
    gun_ids = [ana_no] if ana else idler
    gunler = ([bas + datetime.timedelta(days=i) for i in range((min(bit, bas + datetime.timedelta(days=61)) - bas).days + 1)]
              if (bit - bas).days <= 61 and bas != bit else [])
    menu_ids = (sube_ids if ana else idler) if urunler else []

    isler = [ozet_is(c, bas, bit) for c in idler] + [ozet_is(c, bas, bit) for c in kirilim_ids]
    isler += [kategori_is(c, bas, bit, ana_no) for c in idler]
    if urunler:
        isler += [urun_is(c, bas, bit, ana_no) for c in idler]
        isler += [menu_is(c) for c in menu_ids]
    isler += [ozet_is(c, g, g) for g in gunler for c in gun_ids]

    sonuc = coklu(isler)
    n, k = len(idler), len(kirilim_ids)
    pos = 0
    ozetler, pos = sonuc[pos:pos + n], pos + n
    kirilim, pos = sonuc[pos:pos + k], pos + k
    kategoriler, pos = sonuc[pos:pos + n], pos + n
    urun_ham = menu_ham = []
    if urunler:
        urun_ham, pos = sonuc[pos:pos + n], pos + n
        menu_ham, pos = sonuc[pos:pos + len(menu_ids)], pos + len(menu_ids)
    gunluk_ham = sonuc[pos:pos + len(gunler) * len(gun_ids)]

    veri = {'ana': ana, 'idler': idler}
    veri['ozet'] = ozetleri_topla([ozet_sadelestir(o) for o in ozetler])
    veri['ozet']['ort'] = ortalama(veri['ozet'])
    veri['subeler'] = sorted(({'id': c, 'ad': adlar.get(c, str(c)), **o, 'ort': ortalama(o)}
                              for c, o in ((c, ozet_sadelestir(x)) for c, x in zip(kirilim_ids, kirilim))), key=lambda x: -x['ciro'])
    gsonuc = []
    m = len(gun_ids) or 1
    for i, g in enumerate(gunler):
        parca = [ozet_sadelestir(o) for o in gunluk_ham[i * m:(i + 1) * m]]
        gsonuc.append((g, ozetleri_topla(parca)))
    veri['gunluk'] = gsonuc
    veri['kategoriler'] = kategorileri_birlestir(kategoriler)
    if urunler:
        veri['urunler'] = urunleri_birlestir(urun_ham)
        try:
            veri['satilmayan'] = _satilmayanlar_isle(menu_ham, veri['urunler'])
            veri['satilmayan_hata'] = ''
        except MenuluxHata as e:
            veri['satilmayan'], veri['satilmayan_hata'] = [], str(e)
        except Exception:
            log.exception('Satılmayan ürün hesabı')
            veri['satilmayan'], veri['satilmayan_hata'] = [], 'Menü ürün listesi okunamadı.'
    return veri


def coklu_ozet(idler, araliklar):
    """araliklar: [(bas,bit),...]. Her aralık için idler kapsamının toplam özeti (ort dahil)."""
    isler = [ozet_is(c, b, e) for (b, e) in araliklar for c in idler]
    sonuc = coklu(isler)
    n = len(idler)
    cikti = []
    for i in range(len(araliklar)):
        parca = [ozet_sadelestir(o) for o in sonuc[i * n:(i + 1) * n]]
        t = ozetleri_topla(parca)
        t['ort'] = ortalama(t)
        cikti.append(t)
    return cikti


def coklu_kategori(idler, araliklar, ana_no):
    """araliklar: [(bas,bit),...]. Her aralık için idler kapsamının kategori kırılımı."""
    isler = [kategori_is(c, b, e, ana_no) for (b, e) in araliklar for c in idler]
    sonuc = coklu(isler)
    n = len(idler)
    return [kategorileri_birlestir(sonuc[i * n:(i + 1) * n]) for i in range(len(araliklar))]


def _kirilimi_adlandir(sube_ids, sonuc, adlar):
    liste = []
    for c, o in zip(sube_ids, sonuc):
        oz = ozet_sadelestir(o); oz['ort'] = ortalama(oz)
        liste.append({'id': c, 'ad': adlar.get(c, str(c)), **oz})
    return sorted(liste, key=lambda x: -x['ciro'])


def sube_kirilimi(sube_ids, bas, bit, adlar):
    """Seçili tek bir aralıkta şube bazlı kırılım (ciroya göre sıralı)."""
    if not sube_ids:
        return []
    sonuc = coklu([ozet_is(c, bas, bit) for c in sube_ids])
    return _kirilimi_adlandir(sube_ids, sonuc, adlar)


def tablo_verisi(idler, ozet_araliklari, kategori_araliklari, ana_no, kirilim_ids, kirilim_araligi, adlar):
    """Satış tablosu ekranı için özet + kategori + şube kırılımı işlerinin tek bir toplu (coklu) çağrıda,
    aynı thread havuzu dalgasında çekilmesi — önceden üç ayrı sıralı coklu() çağrısı (3 ayrı dalga) olduğundan
    sayfa yavaş açılıyordu; artık hepsi birlikte paralel çekiliyor. Döner: (ozetler, kategori_liste, subeler)."""
    n = len(idler)
    isler = [ozet_is(c, b, e) for (b, e) in ozet_araliklari for c in idler]
    isler += [kategori_is(c, b, e, ana_no) for (b, e) in kategori_araliklari for c in idler]
    kb, ke = kirilim_araligi
    isler += [ozet_is(c, kb, ke) for c in kirilim_ids]
    sonuc = coklu(isler)
    m, nk = len(ozet_araliklari), len(kategori_araliklari)
    ozet_ham = sonuc[:n * m]
    kategori_ham = sonuc[n * m:n * m + n * nk]
    kirilim_ham = sonuc[n * m + n * nk:]
    ozetler = []
    for i in range(m):
        parca = [ozet_sadelestir(o) for o in ozet_ham[i * n:(i + 1) * n]]
        t = ozetleri_topla(parca); t['ort'] = ortalama(t)
        ozetler.append(t)
    kategori_liste = [kategorileri_birlestir(kategori_ham[i * n:(i + 1) * n]) for i in range(nk)]
    return ozetler, kategori_liste, _kirilimi_adlandir(kirilim_ids, kirilim_ham, adlar)


def eslestirme_onerisi(panel_subeleri, mx_subeleri):
    """Panel şubesi adına en yakın Menulux şubesi (yalnızca öneri)."""
    oneri = {}
    for s in panel_subeleri:
        en, skor = None, 0.0
        for b in mx_subeleri:
            r = difflib.SequenceMatcher(None, _ad_anahtar(s.ad), _ad_anahtar(b['ad'])).ratio()
            if r > skor:
                en, skor = b, r
        if en and skor >= 0.55:
            oneri[s.id] = en['id']
    return oneri


# ------------------------------------------------------------------ ikram / iptal / iade detayı
def personel_is(cid):
    """Şube personeli: {StaffID: 'Ad Soyad'} (ikram/iptal'ı kimin yaptığını göstermek için).
    Not: Anahtarlar STRING tutuluyor — JSON önbelleğe yazılıp geri okunduğunda int anahtarlar
    string'e dönüştüğü için, baştan string olmazsa önbellekten gelen sonuçlarda eşleşme kaybolur."""
    def al():
        veri = _get('StaffAPI/Get', customerID=cid)
        if not isinstance(veri, list):
            return {}
        return {str(s['StaffID']): ('%s %s' % (s.get('Name') or '', s.get('Surname') or '')).strip()
                for s in veri if s.get('StaffID')}
    return ('personel:%s' % cid, datetime.timedelta(hours=6), al)


def siparisler_is(cid, bas, bit):
    """Bir şubenin seçili aralıktaki TÜM sipariş satırları (ikram/iptal/iade ayıklaması bunlardan yapılır).
    Not: Bu uç nokta yalnız gerçek şube id'siyle çalışır — merkez (ana) toplam id'siyle boş döner,
    bu yüzden 'tüm şubeler' seçiminde her şube için ayrı ayrı çağrılması gerekir."""
    def al():
        veri = _get('ReportAPI/GetAllOrders', customerID=cid, startDate=_t(bas), endDate=_t(bit, True))
        return veri if isinstance(veri, list) else []
    return ('siparis:%s:%s:%s' % (cid, bas, bit), _ttl(bit), al)


def _siparisleri_ayikla(ham, personel_adlari, sube_adlari):
    """ham: [(cid, [sipariş satırları]), ...]. İkram/iptal/iade satırlarını (kime/açıklama/kim ile) çıkarır."""
    satirlar = []
    for cid, siparisler in ham:
        adlar = personel_adlari.get(cid, {})
        for s in siparisler:
            if s.get('Gifted'):
                tur = 'ikram'
            elif s.get('Cancelled'):
                tur = 'iptal'
            elif s.get('Returned'):
                tur = 'iade'
            else:
                continue
            staff_id = str(s.get('StaffID')) if s.get('StaffID') is not None else None
            satirlar.append({
                'tur': tur, 'sube': sube_adlari.get(cid, str(cid)),
                'urun': (s.get('ProductName') or s.get('Name') or '').strip(),
                'adet': abs(_f(s.get('Quantity'))), 'tutar': abs(_f(s.get('TotalPrice'))),
                'zaman': s.get('OrderTime') or '', 'masa': (s.get('TableName') or '').strip(),
                'aciklama': (s.get('Description') or '').strip(),
                'personel': adlar.get(staff_id, ''),
            })
    satirlar.sort(key=lambda x: x['zaman'], reverse=True)
    return satirlar


def ikram_iptal(idler, bas, bit, adlar):
    """idler: GERÇEK Menulux şube id'leri (merkez/ana toplam id'si DEĞİL — her şube kendi listesini döner).
    Döner: {'ikram': [...], 'iptal': [...], 'iade': [...]} (her biri en yeniden eskiye sıralı)."""
    if not idler:
        return {'ikram': [], 'iptal': [], 'iade': []}
    n = len(idler)
    isler = [siparisler_is(c, bas, bit) for c in idler] + [personel_is(c) for c in idler]
    sonuc = coklu(isler)
    ham = list(zip(idler, sonuc[:n]))
    personel_adlari = dict(zip(idler, sonuc[n:]))
    satirlar = _siparisleri_ayikla(ham, personel_adlari, adlar)
    cikti = {'ikram': [], 'iptal': [], 'iade': []}
    for s in satirlar:
        cikti[s['tur']].append(s)
    return cikti


# ------------------------------------------------------------------ Rapor Özeti (Menulux'un gösterge paneli)
def gunluk_grafik_is(cid):
    """Son günlerin günlük ciro grafiği (Menulux'un kendi varsayılan penceresi, ~son 7 gün)."""
    def al():
        veri = _get('ReportAPI/GetSalesChart', customerID=cid, type=0)
        return veri if isinstance(veri, list) else []
    return ('grafik:%s' % cid, datetime.timedelta(minutes=30), al)


def saatlik_kanal_is(cid, bas, bit):
    """Saat bazlı kasa/paket kırılımı + satış noktası adı (Rapor Özeti'ndeki 'Kanal Bazlı' ve
    'Satış Noktaları' grafiklerinin kaynağı)."""
    def al():
        veri = _get('ReportAPI/GetSessionPriceTimePoint', customerID=cid, startDate=_t(bas), endDate=_t(bit, True), type=0)
        return veri if isinstance(veri, list) else []
    return ('saatlik:%s:%s:%s' % (cid, bas, bit), _ttl(bit), al)


def ozet_verisi(kapsam, bas, bit):
    """'Rapor Özeti' sayfası: rapor()'daki her şey + haftalık grafik + saatlik kanal/nokta kırılımı,
    TEK coklu() dalgasında (ayrı ayrı çekilseydi sayfa yine yavaşlardı)."""
    ana = kapsam == 'tum'
    ana_no = ana_id()
    idler = [ana_no] if ana else list(kapsam)
    adlar = {b['id']: b['ad'] for b in subeler()}
    sube_ids = list(adlar) if ana else idler
    kirilim_ids = sube_ids if (ana or len(idler) > 1) else []
    menu_ids = sube_ids if ana else idler

    isler = [ozet_is(c, bas, bit) for c in idler] + [ozet_is(c, bas, bit) for c in kirilim_ids]
    isler += [kategori_is(c, bas, bit, ana_no) for c in idler]
    isler += [urun_is(c, bas, bit, ana_no) for c in idler]
    isler += [menu_is(c) for c in menu_ids]
    isler += [gunluk_grafik_is(c) for c in idler]
    isler += [saatlik_kanal_is(c, bas, bit) for c in idler]

    sonuc = coklu(isler)
    n, k, mn = len(idler), len(kirilim_ids), len(menu_ids)
    pos = 0
    ozetler, pos = sonuc[pos:pos + n], pos + n
    kirilim, pos = sonuc[pos:pos + k], pos + k
    kategoriler, pos = sonuc[pos:pos + n], pos + n
    urun_ham, pos = sonuc[pos:pos + n], pos + n
    menu_ham, pos = sonuc[pos:pos + mn], pos + mn
    grafik_ham, pos = sonuc[pos:pos + n], pos + n
    kanal_ham, pos = sonuc[pos:pos + n], pos + n

    veri = {'ana': ana, 'idler': idler}
    veri['ozet'] = ozetleri_topla([ozet_sadelestir(o) for o in ozetler])
    veri['ozet']['ort'] = ortalama(veri['ozet'])
    veri['subeler'] = _kirilimi_adlandir(kirilim_ids, kirilim, adlar)
    veri['kategoriler'] = kategorileri_birlestir(kategoriler)
    veri['urunler'] = urunleri_birlestir(urun_ham)
    try:
        veri['satilmayan'] = _satilmayanlar_isle(menu_ham, veri['urunler'])
    except Exception:
        log.exception('Satılmayan ürün hesabı (özet)')
        veri['satilmayan'] = []

    toplam = {}
    for liste in grafik_ham:
        for g in liste:
            t = (g.get('BusinessDate') or '')[:10]
            if t:
                toplam[t] = toplam.get(t, 0.0) + _f(g.get('TotalPrice'))
    veri['grafik'] = sorted(toplam.items())

    saat = {h: {'kasa': 0.0, 'paket': 0.0} for h in range(24)}
    nokta = {}
    for liste in kanal_ham:
        for r in liste:
            try:
                h = int(r.get('SessionTime') or 0) % 24
            except (TypeError, ValueError):
                h = 0
            saat[h]['kasa'] += _f(r.get('SessionRegisterPrice'))
            saat[h]['paket'] += _f(r.get('SessionPackagePrice'))
            ad = (r.get('PointName') or '').strip() or 'Diğer'
            nokta[ad] = nokta.get(ad, 0.0) + _f(r.get('SessionTotalPrice'))
    veri['saatlik'] = [{'saat': h, 'kasa': v['kasa'], 'paket': v['paket']} for h, v in sorted(saat.items()) if v['kasa'] or v['paket']]
    toplam_nokta = sum(nokta.values()) or 1
    veri['noktalar'] = sorted(({'ad': ad, 'tutar': t, 'pay': t / toplam_nokta * 100} for ad, t in nokta.items()), key=lambda x: -x['tutar'])
    return veri
