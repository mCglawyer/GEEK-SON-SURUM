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
import unicodedata
from concurrent.futures import ThreadPoolExecutor

import requests
from django.utils import timezone

log = logging.getLogger(__name__)

PORTAL = 'https://portal.menulux.com'
API = 'https://menuluxportalapi.azurewebsites.net'
ZAMAN_ASIMI = 25
_kilit = threading.Lock()
_oturum = {'authkey': None, 'zaman': 0.0}
OTURUM_OMRU = 25 * 60   # sn; süre dolmadan yenilenir, 401/403'te de yeniden girilir


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


def _giris(a):
    s = requests.Session()
    try:
        r = s.get(PORTAL + '/Configuration/GeneratePublicKey', timeout=ZAMAN_ASIMI,
                  headers={'X-Requested-With': 'XMLHttpRequest', 'Referer': PORTAL + '/Account/Login'})
        pk = r.json().get('PublicKey')
        if not pk:
            raise MenuluxHata('Menulux giriş anahtarı alınamadı.')
        r = s.post(API + '/api/UserAPI/LoginUser', timeout=ZAMAN_ASIMI,
                   json={'UserName': a['kullanici'], 'Password': a['sifre'], 'UserLog': True, 'OTPCode': None, 'UserID': None},
                   headers={'Publickey': pk, 'Origin': PORTAL, 'Referer': PORTAL + '/'})
    except requests.RequestException as e:
        raise MenuluxHata('Menulux\'a ulaşılamadı (%s).' % e.__class__.__name__)
    except ValueError:
        raise MenuluxHata('Menulux giriş yanıtı okunamadı.')
    if r.status_code == 202:
        raise MenuluxHata('Menulux hesabı SMS doğrulaması istiyor; otomatik giriş yapılamaz.')
    if r.status_code != 200:
        raise MenuluxHata('Menulux girişi reddedildi (HTTP %s). Kullanıcı adı/şifreyi kontrol edin.' % r.status_code)
    ak = r.headers.get('AuthKey')
    if not ak:
        raise MenuluxHata('Menulux giriş yanıtında oturum anahtarı yok.')
    return ak


def _authkey(yenile=False):
    with _kilit:
        simdi = timezone.now().timestamp()
        if yenile or not _oturum['authkey'] or simdi - _oturum['zaman'] > OTURUM_OMRU:
            _oturum['authkey'] = _giris(_ana())
            _oturum['zaman'] = simdi
        return _oturum['authkey']


def oturumu_sifirla():
    with _kilit:
        _oturum['authkey'] = None


def _get(yol, **params):
    a = _ana()
    for deneme in (0, 1):
        ak = _authkey(yenile=bool(deneme))
        try:
            r = requests.get(API + '/api/' + yol, params=params, timeout=ZAMAN_ASIMI,
                             headers={'AuthKey': ak, 'CustomerID': str(a['ana']), 'Origin': PORTAL, 'Referer': PORTAL + '/',
                                      'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json'})
        except requests.RequestException as e:
            raise MenuluxHata('Menulux\'a ulaşılamadı (%s).' % e.__class__.__name__)
        if r.status_code in (401, 403) and deneme == 0:
            continue
        if r.status_code != 200:
            raise MenuluxHata('Menulux isteği başarısız (HTTP %s: %s).' % (r.status_code, yol.split('?')[0]))
        try:
            return r.json()
        except ValueError:
            raise MenuluxHata('Menulux yanıtı okunamadı (%s).' % yol)
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
    sonuc = [None] * len(isler)
    eksik = []
    for i, (anahtar, ttl, fn) in enumerate(isler):
        var, veri = _oku(anahtar, ttl)
        if var:
            sonuc[i] = veri
        else:
            eksik.append(i)
    if eksik:
        if len(eksik) == 1:
            cekilen = [isler[eksik[0]][2]()]
        else:
            with ThreadPoolExecutor(max_workers=min(6, len(eksik))) as ex:
                cekilen = list(ex.map(lambda i: isler[i][2](), eksik))
        for i, veri in zip(eksik, cekilen):
            sonuc[i] = veri
            _yaz(isler[i][0], veri)
    return sonuc


# ------------------------------------------------------------------ ham veri
def subeler():
    """Menulux şubeleri: [{'id', 'ad'}] (merkez hariç, silinmişler hariç)."""
    a = _ana()

    def al():
        veri = _get('CustomerAPI/GetSortedBranches', customerID=a['ana'], sortByRevenue='false')
        return [{'id': int(b['CustomerID']), 'ad': (b.get('Name') or '').strip()} for b in veri
                if b.get('CustomerID') and int(b['CustomerID']) != a['ana'] and not b.get('Deleted')]
    return sorted(onbellekli('subeler', datetime.timedelta(hours=1), al), key=lambda b: b['ad'])


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
    """Şubenin varsayılan menüsündeki ürünler (satılmayan ürün raporu için)."""
    def al():
        menuler = _get('MenuAPI/GetMenusSummary', customerID=cid)
        menuler = menuler if isinstance(menuler, list) else []
        secili = next((m for m in menuler if m.get('Dafault')), menuler[0] if menuler else None)
        if not secili:
            return []
        veri = _get('OfferAPI/GetProducts', customerID=cid, menuID=secili['MenuID'])
        return veri if isinstance(veri, list) else []
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


def satilmayanlar(idler, satilan_urunler):
    """Menüde olup aralıkta hiç satılmayan ürünler. Eşleşme: ürün kodu, olmazsa ad."""
    kodlar = {u['kod'] for u in satilan_urunler if u['kod']}
    adlar = {_ad_anahtar(u['ad']) for u in satilan_urunler}
    gorulen, sonuc = set(), []
    for menu in coklu([menu_is(c) for c in idler]):
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
    """kapsam: 'tum' (merkez toplamı) ya da şube numaraları listesi. Tek sözlükte tüm rapor verisi."""
    ana = kapsam == 'tum'
    ana_no = ana_id()
    idler = [ana_no] if ana else list(kapsam)
    adlar = {b['id']: b['ad'] for b in subeler()}
    sube_ids = list(adlar) if ana else idler
    kirilim_ids = sube_ids if (ana or len(idler) > 1) else []
    isler = [ozet_is(c, bas, bit) for c in idler] + [ozet_is(c, bas, bit) for c in kirilim_ids]
    isler += [kategori_is(c, bas, bit, ana_no) for c in idler]
    if urunler:
        isler += [urun_is(c, bas, bit, ana_no) for c in idler]
    sonuc = coklu(isler)
    n, k = len(idler), len(kirilim_ids)
    ozetler, kirilim, kategoriler = sonuc[:n], sonuc[n:n + k], sonuc[n + k:n + k + n]
    veri = {'ana': ana, 'idler': idler}
    veri['ozet'] = ozetleri_topla([ozet_sadelestir(o) for o in ozetler])
    veri['ozet']['ort'] = ortalama(veri['ozet'])
    veri['subeler'] = sorted(({'id': c, 'ad': adlar.get(c, str(c)), **o, 'ort': ortalama(o)}
                              for c, o in ((c, ozet_sadelestir(x)) for c, x in zip(kirilim_ids, kirilim))), key=lambda x: -x['ciro'])
    veri['gunluk'] = gunluk(idler, bas, bit, ana) if (bit - bas).days <= 61 and bas != bit else []
    veri['kategoriler'] = kategorileri_birlestir(kategoriler)
    if urunler:
        veri['urunler'] = urunleri_birlestir(sonuc[n + k + n:])
        try:
            veri['satilmayan'] = satilmayanlar(sube_ids if ana else idler, veri['urunler'])
            veri['satilmayan_hata'] = ''
        except MenuluxHata as e:
            veri['satilmayan'], veri['satilmayan_hata'] = [], str(e)
        except Exception:
            log.exception('Satılmayan ürün hesabı')
            veri['satilmayan'], veri['satilmayan_hata'] = [], 'Menü ürün listesi okunamadı.'
    return veri


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
