"""Temizlik malzemesi tüketimi.

Mantık (Excel'deki "Temizlik Malzemesi Stok Takip Çizelgesi" ile aynı):
  1. Ay başında, ilk sevkiyatı almadan 1 gün önce şube SAYIM yapar  -> İlk stok
  2. Her hafta gelen sevkiyat "İlave" olur. Bu sütun sevkiyat kayıtlarından kendiliğinden dolar
     (çıkışı onaylanmış / teslim edilmiş siparişler); sevkiyat dışı gelen ya da hatalı olan miktar
     "Düzeltme" ile eklenir/çıkarılır.
  3. 4 hafta sonunda ikinci SAYIM yapılır                          -> Son stok
  4. Kullanım = İlk stok + İlave + Düzeltme − Son stok

Sayım tarihinden SONRA gelen sevkiyatlar ilave sayılır (sayım günü gelen sevkiyat bir sonraki döneme girer).
Hafta/gün kırılımında İLAVE kesindir; tüketim yalnızca iki sayım arasında bilinir, bu yüzden hafta ve gün
görünümündeki tüketim, o dönemin toplam kullanımının günlere eşit dağıtılmış TAHMİNİDİR.
"""
import calendar
import datetime
import io
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db.models import DateTimeField
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import (Rol, SevkiyatBirim, SevkiyatDurumu, SevkiyatKalem, Sube, TemizlikAyar, TemizlikDuzeltme,
                     TemizlikFiyat, TemizlikSayim, TemizlikUrun)
from .sevkiyat_analiz import ay_etiketi, ay_komsulari, ay_oku, sayi_yaz  # noqa: F401  (ekranlar buradan alır)

GIRIS_ROLLERI = (Rol.SEF, Rol.MAGAZA_MUDURU, Rol.GENEL_MUDUR, Rol.OPERATOR)
RAPOR_ROLLERI = (Rol.YATIRIMCI, Rol.SATIN_ALMA, Rol.GENEL_MUDUR, Rol.MUDUR, Rol.OPERATOR, Rol.SEF, Rol.MAGAZA_MUDURU)
URUN_ROLLERI = (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.SATIN_ALMA)
FIYAT_GOR = (Rol.SATIN_ALMA, Rol.YATIRIMCI, Rol.MUDUR, Rol.OPERATOR, Rol.GENEL_MUDUR)   # fiyatı ve tutarı görenler
FIYAT_YAZ = (Rol.SATIN_ALMA, Rol.GENEL_MUDUR)                                         # fiyatı girebilenler
AYAR_ROLLERI = (Rol.GENEL_MUDUR, Rol.OPERATOR)                                        # aç/kapa, başlangıç, sıfırlama
YONETIM_ROLLERI = (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.SATIN_ALMA)                     # sistem kapalıyken de girebilenler
GORUNUMLER = (('aylik', 'Aylık'), ('haftalik', 'Haftalık'), ('gunluk', 'Günlük'))

_GELEN_DURUMLAR = (SevkiyatDurumu.ONAYLANDI, SevkiyatDurumu.TESLIM)
_SIFIR = Decimal('0')
_TR = str.maketrans({'İ': 'i', 'I': 'i', 'ı': 'i', 'Ç': 'c', 'ç': 'c', 'Ş': 's', 'ş': 's',
                     'Ğ': 'g', 'ğ': 'g', 'Ö': 'o', 'ö': 'o', 'Ü': 'u', 'ü': 'u'})
_GUN_AD = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']


def sade(metin):
    return ' '.join(str(metin or '').translate(_TR).lower().split())


# ----------------------------------------------------------------------------- yetki
def fiyat_gorur(personel):
    return personel is not None and personel.rol in FIYAT_GOR


def fiyat_yazar(personel):
    return personel is not None and personel.rol in FIYAT_YAZ


def erisebilir(personel, ayar):
    """Sistem kapalıyken yalnızca yönetim (GM, Operatör, Satın Alma) içeri girer."""
    return bool(ayar.aktif) or (personel is not None and personel.rol in YONETIM_ROLLERI)


def baslamamis(ayar, ay_ilk):
    """Başlangıç ayından önceki aylara kayıt girilemez."""
    return bool(ayar.baslangic and ay_ilk < ayar.baslangic.replace(day=1))


def varsayilan_ay(ayar):
    """Ay seçilmemişse: bu ay; sistem henüz başlamadıysa başlangıç ayı."""
    bugun = ay_oku(None)
    if ayar.baslangic and bugun < ayar.baslangic.replace(day=1):
        return ayar.baslangic.replace(day=1)
    return bugun


def _depo_disi():
    return Sube.objects.filter(depo_mu=False).order_by('ad')


def giris_subeleri(personel):
    """Sayım ve düzeltme girebileceği şubeler."""
    if personel is None or personel.rol not in GIRIS_ROLLERI:
        return []
    if personel.rol in (Rol.GENEL_MUDUR, Rol.OPERATOR):
        return list(_depo_disi())
    if personel.rol == Rol.MAGAZA_MUDURU and personel.sorumlu_subeler.exists():
        return list(personel.sorumlu_subeler.order_by('ad'))
    return [personel.sube] if personel.sube_id else []


def rapor_subeleri(personel):
    """Tüketim raporunda görebileceği şubeler."""
    if personel is None or personel.rol not in RAPOR_ROLLERI:
        return []
    if personel.rol in (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI, Rol.SATIN_ALMA):
        return list(_depo_disi())
    if personel.rol == Rol.MUDUR:
        return list(personel.sorumlu_subeler.filter(depo_mu=False).order_by('ad'))
    if personel.rol == Rol.MAGAZA_MUDURU and personel.sorumlu_subeler.exists():
        return list(personel.sorumlu_subeler.order_by('ad'))
    return [personel.sube] if personel.sube_id else []


# ----------------------------------------------------------------------------- sayı yardımcıları
def sayi_oku(metin):
    """'12', '12,5', '1.250,5' -> Decimal; boş -> None; bozuk/negatif/aşırı -> ValueError."""
    t = (metin or '').strip().replace(' ', '')
    if not t:
        return None
    if ',' in t:
        t = t.replace('.', '').replace(',', '.')
    try:
        d = Decimal(t)
    except InvalidOperation:
        raise ValueError(metin)
    if not d.is_finite() or abs(d) > Decimal('10000000'):
        raise ValueError(metin)
    return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def girdi_yaz(d):
    """Form kutusuna konacak değer: 12 -> '12', 12.5 -> '12,5'."""
    if d is None:
        return ''
    s = '{:f}'.format(Decimal(d).quantize(Decimal('0.01')))
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s.replace('.', ',')


BIRIMLER = ('ADET', 'PAKET', 'SET', 'KUTU')
KAPASITE_BIRIMLERI = ('ML', 'LT', 'GR', 'KG')


def toplam_adet(urun, koli, adet, acik):
    """Sayım satırı -> ürünün birimi (adet/paket/set) cinsinden toplam.

    koli  : kapalı koli sayısı           (× koli içeriği)
    adet  : kapalı, tek tek sayılan adet
    acik  : açılmış kaplarda KALAN toplam miktar (kapasite biriminde: ml, kg ...). Kapasiteye bölünüp adet olur:
            10 kapalı + 300 ml açık, kapasite 500 ml  ->  10 + 0,6 = 10,6
    """
    t = (koli or _SIFIR) * (urun.koli_icerigi or 1) + (adet or _SIFIR)
    if acik and urun.hacim:
        t += acik / urun.hacim
    return t.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def hacim_karsiligi(adet_miktar, urun):
    """12,4 adet (500 ml'lik) -> '≈ 6.200 ml'. Kapasitesi tanımsız ürünlerde boş."""
    if adet_miktar is None or not urun.hacim:
        return ''
    return '≈ %s %s' % (sayi_yaz(adet_miktar * urun.hacim), (urun.hacim_birim or '').lower())


def sayim_degerleri(sayim):
    """Kayıtlı sayımı forma geri koyar: urun_id -> (koli, adet, acik). Eski (yalnız toplam girilmiş) kayıtlar adet sayılır."""
    cikti = {}
    if sayim is None:
        return cikti
    for k in sayim.kalemler.all():
        if k.urun_id is None:
            continue
        if k.koli is None and k.adet is None and k.acik is None:
            cikti[k.urun_id] = (None, k.miktar, None)
        else:
            cikti[k.urun_id] = (k.koli, k.adet, k.acik)
    return cikti


def ay_sonu(ay_ilk):
    return ay_ilk.replace(day=calendar.monthrange(ay_ilk.year, ay_ilk.month)[1])


def sayim_tarihi_gecerli(tur, tarih, ay_ilk):
    """İlk sayım ayın başına, son sayım ayın sonuna yakın olmalı (±10 gün)."""
    sinir = ay_ilk if tur == 'ILK' else ay_sonu(ay_ilk)
    return abs((tarih - sinir).days) <= 10


# ----------------------------------------------------------------------------- fiyat
_KG = {'KG': Decimal('1'), 'GR': Decimal('0.001')}
_LT = {'LT': Decimal('1'), 'ML': Decimal('0.001')}


def fiyat_birimi_uygun(urun, birim):
    """Fiyat birimi ürünün kapasitesiyle hesaplanabilir mi? (KG için kg/gr, LT için lt/ml kapasite gerekir.)"""
    if birim == 'ADET':
        return True
    if not urun.hacim:
        return False
    return (urun.hacim_birim in (_KG if birim == 'KG' else _LT))


def adet_fiyati(urun, fiyat, birim):
    """Fiyatı ürünün sayım birimi (adet/paket/set) başına TL'ye çevirir; çevrilemezse None."""
    if fiyat is None:
        return None
    if birim == 'ADET':
        return fiyat
    if not fiyat_birimi_uygun(urun, birim):
        return None
    katsayi = (_KG if birim == 'KG' else _LT)[urun.hacim_birim]
    return (fiyat * urun.hacim * katsayi).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def fiyat_haritasi(ay_ilk=None):
    """urun_id -> {fiyat, birim, gecerli, adet}. ay_ilk verilirse o ayın sonunda geçerli fiyat (yoksa en eski kayıt);
    verilmezse en güncel fiyat."""
    son = ay_sonu(ay_ilk) if ay_ilk else None
    secilen, ilk = {}, {}
    for f in TemizlikFiyat.objects.select_related('urun').order_by('urun_id', 'gecerli'):
        ilk.setdefault(f.urun_id, f)
        if son is None or f.gecerli <= son:
            secilen[f.urun_id] = f
    for uid, f in ilk.items():
        secilen.setdefault(uid, f)
    return {uid: {'fiyat': f.fiyat, 'birim': f.birim, 'gecerli': f.gecerli,
                  'adet': adet_fiyati(f.urun, f.fiyat, f.birim)} for uid, f in secilen.items()}


def para_yaz(d):
    """1250.5 -> '1.250,50'"""
    if d is None:
        return '—'
    s = '{:,.2f}'.format(Decimal(d).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    return s.replace(',', '§').replace('.', ',').replace('§', '.')


# ----------------------------------------------------------------------------- hesap
def _adet(k, tu, miktar, birim):
    """Sevkiyat miktarını ürünün taban birimine (adet/paket/set) çevirir."""
    u = k.urun
    if u is not None and u.ust_birim and u.ust_birim != u.birim and birim == u.ust_birim:
        return miktar * Decimal(k.koli_icerigi or u.koli_icerigi or 1)
    if u is None and birim == SevkiyatBirim.KOLI:
        return miktar * Decimal(k.koli_icerigi or tu.koli_icerigi or 1)
    return miktar


def _gelen_miktar(k):
    if k.sevkiyat_miktar is not None:
        return k.sevkiyat_miktar, (k.sevkiyat_birim or k.istenen_birim)
    if k.satinalma_miktar is not None:
        return k.satinalma_miktar, (k.satinalma_birim or k.istenen_birim)
    return (k.istenen_miktar or _SIFIR), k.istenen_birim


def _aralik_gunleri(bas, bit):
    """(bas, bit] aralığındaki günler."""
    n = (bit - bas).days
    return [bas + datetime.timedelta(days=i) for i in range(1, n + 1)]


def veri_hesapla(subeler, ay_ilk, bugun=None, fiyatli=False):
    """Seçili şubeler için ay verisi.

    Dönen sözlük:
      subeler : [ {sube, ilk, son, bas, bit, tam, satirlar:[...] } ]   satır = ürün bazında
      urunler : katalog (veri olan/aktif)
      toplam  : tüm şubelerin ürün bazında toplamı (aynı satır biçimi)
      eslesmeyen : sevkiyatta 'Temizlik' formunda olup kataloğa bağlanamayan ürün adları
      fiyatli=True ise satırlara birim fiyat + tutar (TL) eklenir; yalnızca fiyatı görmeye yetkili roller için istenir.
    """
    bugun = bugun or timezone.localdate()
    baslangic = TemizlikAyar.al().baslangic
    son_gun = ay_sonu(ay_ilk)
    ids = [s.id for s in subeler]
    tum_urunler = list(TemizlikUrun.objects.all())
    bagli = {u.urun_id: u for u in tum_urunler if u.urun_id}
    adli = {sade(u.ad): u for u in tum_urunler}

    sayimlar = {}
    for sy in TemizlikSayim.objects.filter(sube_id__in=ids, ay=ay_ilk).prefetch_related('kalemler'):
        sayimlar[(sy.sube_id, sy.tur)] = (sy, {k.urun_id: k.miktar for k in sy.kalemler.all() if k.urun_id})

    donemler = {}
    for s in subeler:
        ilk = sayimlar.get((s.id, 'ILK'), (None, {}))[0]
        son = sayimlar.get((s.id, 'SON'), (None, {}))[0]
        bas = ilk.tarih if ilk else ay_ilk - datetime.timedelta(days=1)
        bit = son.tarih if son else min(bugun, son_gun)
        if bit < bas:
            bit = bas
        donemler[s.id] = (bas, bit)

    gunluk = {}          # (sube_id, urun_id) -> {tarih: miktar}   (sevkiyat)
    gun_duz = {}         # (sube_id, urun_id) -> {tarih: miktar}   (düzeltme)
    eslesmeyen = {}
    if ids:
        alt = min(b for b, _ in donemler.values()) + datetime.timedelta(days=1)
        ust = max(t for _, t in donemler.values())
        tz = timezone.get_current_timezone()
        pen_bas = timezone.make_aware(datetime.datetime.combine(alt, datetime.time.min), tz)
        pen_bit = timezone.make_aware(datetime.datetime.combine(ust + datetime.timedelta(days=1), datetime.time.min), tz)
        qs = (SevkiyatKalem.objects
              .filter(talep__sube_id__in=ids, talep__durum__in=_GELEN_DURUMLAR)
              .annotate(_eff=Coalesce('talep__onay_tarih', 'talep__sevkiyat_tarih', 'talep__olusturma',
                                      output_field=DateTimeField()))
              .filter(_eff__gte=pen_bas, _eff__lt=pen_bit)
              .select_related('talep', 'urun'))
        for k in qs:
            gun = timezone.localtime(k._eff).date()
            bas, bit = donemler[k.talep.sube_id]
            if not (bas < gun <= bit):
                continue
            if baslangic and gun < baslangic:
                continue          # sistem başlangıcından önce gelen sevkiyat sayılmaz
            tu = bagli.get(k.urun_id) or adli.get(sade(k.urun_ad or (k.urun.ad if k.urun_id else '')))
            if tu is None:
                if (k.form or '') == 'TEMIZLIK':
                    ad = (k.urun_ad or '—').strip()
                    eslesmeyen[sade(ad)] = ad
                continue
            m, b = _gelen_miktar(k)
            d = gunluk.setdefault((k.talep.sube_id, tu.id), {})
            d[gun] = d.get(gun, _SIFIR) + _adet(k, tu, m, b)
        for dz in TemizlikDuzeltme.objects.filter(sube_id__in=ids, ay=ay_ilk):
            if dz.urun_id is None:
                continue
            bas, bit = donemler[dz.sube_id]
            if not (bas < dz.tarih <= bit) or (baslangic and dz.tarih < baslangic):
                continue          # dönem dışına düşen düzeltme hesaba girmez (ekranda uyarılır)
            d = gun_duz.setdefault((dz.sube_id, dz.urun_id), {})
            d[dz.tarih] = d.get(dz.tarih, _SIFIR) + dz.miktar

    cikti = []
    for s in subeler:
        ilk_sy, ilk_m = sayimlar.get((s.id, 'ILK'), (None, {}))
        son_sy, son_m = sayimlar.get((s.id, 'SON'), (None, {}))
        bas, bit = donemler[s.id]
        tam = bool(ilk_sy and son_sy)
        gun_say = max(1, (bit - bas).days)
        satirlar = []
        for tu in tum_urunler:
            gi = gunluk.get((s.id, tu.id), {})
            gd = gun_duz.get((s.id, tu.id), {})
            ilave = sum(gi.values(), _SIFIR)
            duz = sum(gd.values(), _SIFIR)
            ilk_v = ilk_m.get(tu.id) if ilk_sy else None
            son_v = son_m.get(tu.id) if son_sy else None
            kullanim = None
            if tam:
                kullanim = (ilk_v or _SIFIR) + ilave + duz - (son_v or _SIFIR)
            if not tu.aktif and not (ilave or duz or ilk_v or son_v):
                continue
            gun_ilave = {}
            for d, v in list(gi.items()) + list(gd.items()):
                gun_ilave[d] = gun_ilave.get(d, _SIFIR) + v
            gun_tuketim = {}
            if kullanim is not None:
                pay = kullanim / Decimal(gun_say)
                gun_tuketim = {g: pay for g in _aralik_gunleri(bas, bit)}
            satirlar.append({'urun': tu, 'ilk': ilk_v, 'ilave': ilave, 'duzeltme': duz, 'son': son_v,
                             'kullanim': kullanim, 'gun_ilave': gun_ilave, 'gun_tuketim': gun_tuketim})
        cikti.append({'sube': s, 'ilk': ilk_sy, 'son': son_sy, 'bas': bas, 'bit': bit, 'tam': tam,
                      'satirlar': satirlar})
    fiyat_eksik = {}
    if fiyatli:
        fm = fiyat_haritasi(ay_ilk)

        def tutar_ekle(r):
            f = fm.get(r['urun'].id)
            r['fiyat'] = f
            adet_f = f['adet'] if f else None
            r['adet_fiyat'] = adet_f
            r['tutar'] = (r['kullanim'] * adet_f) if (r['kullanim'] is not None and adet_f is not None) else None
            if adet_f is None and r['kullanim']:
                fiyat_eksik[r['urun'].id] = r['urun'].ad

        for c in cikti:
            for r in c['satirlar']:
                tutar_ekle(r)
            c['tutar'] = sum((r['tutar'] for r in c['satirlar'] if r['tutar'] is not None), _SIFIR) if c['tam'] else None

    toplam = []
    for i, tu in enumerate(tum_urunler):
        satir = {'urun': tu, 'ilk': None, 'ilave': _SIFIR, 'duzeltme': _SIFIR, 'son': None, 'kullanim': None,
                 'gun_ilave': {}, 'gun_tuketim': {}}
        var = False
        for c in cikti:
            r = next((x for x in c['satirlar'] if x['urun'].id == tu.id), None)
            if r is None:
                continue
            var = True
            satir['ilave'] += r['ilave']
            satir['duzeltme'] += r['duzeltme']
            if r['ilk'] is not None:
                satir['ilk'] = (satir['ilk'] or _SIFIR) + r['ilk']
            if r['son'] is not None:
                satir['son'] = (satir['son'] or _SIFIR) + r['son']
            if r['kullanim'] is not None:
                satir['kullanim'] = (satir['kullanim'] or _SIFIR) + r['kullanim']
            for g, v in r['gun_ilave'].items():
                satir['gun_ilave'][g] = satir['gun_ilave'].get(g, _SIFIR) + v
            for g, v in r['gun_tuketim'].items():
                satir['gun_tuketim'][g] = satir['gun_tuketim'].get(g, _SIFIR) + v
        if var and (satir['ilk'] or satir['son'] or satir['ilave'] or satir['duzeltme']):
            if fiyatli:
                satir['fiyat'] = fm.get(tu.id)
                satir['adet_fiyat'] = satir['fiyat']['adet'] if satir['fiyat'] else None
                parcalar = [x['tutar'] for c in cikti for x in c['satirlar'] if x['urun'].id == tu.id and x['tutar'] is not None]
                satir['tutar'] = sum(parcalar, _SIFIR) if parcalar else None
            toplam.append(satir)
    sonuc = {'ay': ay_ilk, 'etiket': ay_etiketi(ay_ilk), 'subeler': cikti, 'toplam': toplam,
             'tam_sube': sum(1 for c in cikti if c['tam']), 'eslesmeyen': sorted(eslesmeyen.values()),
             'fiyatli': fiyatli}
    if fiyatli:
        sonuc['genel_tutar'] = sum((c['tutar'] for c in cikti if c['tutar'] is not None), _SIFIR)
        sonuc['fiyat_eksik'] = sorted(fiyat_eksik.values())
    return sonuc


def hafta_parcalari(bas, bit):
    """Giriş sayfası: sayımdan sonraki 7'şer günlük 'Hafta 1, Hafta 2 …' sütunları (Excel'deki İLAVE sütunları)."""
    parcalar = []
    bas_g = bas + datetime.timedelta(days=1)
    i = 0
    while bas_g <= bit:
        son_g = min(bas_g + datetime.timedelta(days=6), bit)
        parcalar.append({'ad': '%d. hafta' % (i + 1), 'bas': bas_g, 'bit': son_g,
                         'etiket': '%s–%s' % (bas_g.strftime('%d.%m'), son_g.strftime('%d.%m'))})
        bas_g = son_g + datetime.timedelta(days=1)
        i += 1
    return parcalar


def takvim_parcalari(ay_ilk, gorunum):
    """Rapor: takvim haftaları (Pzt–Paz) ya da günler."""
    son = ay_sonu(ay_ilk)
    if gorunum == 'gunluk':
        gun = ay_ilk
        liste = []
        while gun <= son:
            liste.append({'ad': '%02d' % gun.day, 'bas': gun, 'bit': gun,
                          'etiket': '%02d.%02d %s' % (gun.day, gun.month, _GUN_AD[gun.weekday()])})
            gun += datetime.timedelta(days=1)
        return liste
    liste = []
    bas = ay_ilk
    while bas <= son:
        bit = min(bas + datetime.timedelta(days=6 - bas.weekday()), son)
        liste.append({'ad': '%d. hafta' % (len(liste) + 1), 'bas': bas, 'bit': bit,
                      'etiket': '%s–%s' % (bas.strftime('%d.%m'), bit.strftime('%d.%m'))})
        bas = bit + datetime.timedelta(days=1)
    return liste


def parca_toplam(gun_sozlugu, parca):
    t = _SIFIR
    for g, v in gun_sozlugu.items():
        if parca['bas'] <= g <= parca['bit']:
            t += v
    return t


def sube_kirilimi(veri):
    """Ürün × şube kullanım matrisi (yalnızca tamamlanmış şubeler dolu)."""
    satirlar = []
    for r in veri['toplam']:
        hucre = []
        for c in veri['subeler']:
            x = next((y for y in c['satirlar'] if y['urun'].id == r['urun'].id), None)
            hucre.append(x['kullanim'] if x else None)
        satirlar.append((r['urun'], hucre))
    return satirlar


# ----------------------------------------------------------------------------- Excel / PDF
def _etiket(veri, secili, gorunum):
    ad = dict(GORUNUMLER).get(gorunum, 'Aylık')
    return '%s · %s · %s görünüm' % (veri['etiket'], secili.ad if secili else 'Tüm şubeler', ad)


def _parcalar(veri, gorunum):
    return takvim_parcalari(veri['ay'], gorunum) if gorunum in ('haftalik', 'gunluk') else []


def excel_bytes(veri, secili, gorunum):
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from .excel_logo import excel_logo

    wb = openpyxl.Workbook()
    mavi = PatternFill('solid', fgColor='162AA3')
    zebra = PatternFill('solid', fgColor='F4F6FB')
    ince = Side(style='thin', color='D7DCEB')
    kenar = Border(left=ince, right=ince, top=ince, bottom=ince)

    def sayfa(ws, baslik, basliklar, satirlar, olculer, sayisal_baslangic=2, alt_not='', para=()):
        excel_logo(ws)
        ws['C2'] = baslik
        ws['C2'].font = Font(bold=True, size=14, color='162AA3')
        ws['C3'] = _etiket(veri, secili, gorunum)
        ws['C3'].font = Font(color='6B7280')
        ust = 5
        for i, b in enumerate(basliklar, 1):
            c = ws.cell(row=ust, column=i, value=b)
            c.fill, c.font, c.border = mavi, Font(bold=True, color='FFFFFF'), kenar
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        for r, satir in enumerate(satirlar, ust + 1):
            for i, v in enumerate(satir, 1):
                c = ws.cell(row=r, column=i, value=(float(v) if isinstance(v, Decimal) else v))
                c.border = kenar
                if (r - ust) % 2 == 0:
                    c.fill = zebra
                if i >= sayisal_baslangic:
                    c.number_format = '#,##0.00' if i in para else '#,##0.##'
                    c.alignment = Alignment(horizontal='right')
        for i in range(1, len(basliklar) + 1):
            ws.column_dimensions[get_column_letter(i)].width = olculer[i - 1] if i <= len(olculer) else 11
        ws.freeze_panes = ws.cell(row=ust + 1, column=2)
        if alt_not:
            n = ws.cell(row=ust + len(satirlar) + 2, column=1, value=alt_not)
            n.font = Font(italic=True, color='6B7280')

    fiyatli = veri.get('fiyatli', False)
    ws = wb.active
    ws.title = 'Aylık Özet'
    basliklar = ['Ürün', 'Birim', 'İlk stok', 'İlave (sevkiyat)', 'Düzeltme', 'Son stok', 'Kullanım', 'Kullanım (hacim)']
    olculer = [46, 10, 12, 16, 12, 12, 14, 18]
    satirlar = [[r['urun'].ad, r['urun'].birim, r['ilk'], r['ilave'], r['duzeltme'], r['son'], r['kullanim'],
                 hacim_karsiligi(r['kullanim'], r['urun'])] for r in veri['toplam']]
    para = ()
    not_metni = ('Kullanım = İlk stok + İlave + Düzeltme − Son stok. İlk ve son sayımı girilmemiş şubelerde kullanım '
                 'hesaplanmaz (%d / %d şube tamamlandı).' % (veri['tam_sube'], len(veri['subeler'])))
    if fiyatli:
        basliklar += ['Birim fiyat (TL / adet)', 'Tutar (TL)']
        olculer += [18, 16]
        para = (9, 10)
        for satir, r in zip(satirlar, veri['toplam']):
            satir += [r['adet_fiyat'], r['tutar']]
        satirlar.append(['TOPLAM TUTAR', '', None, None, None, None, None, '', None, veri['genel_tutar']])
        if veri['fiyat_eksik']:
            not_metni += ' Fiyatı girilmemiş ürünler toplama dahil değil: %s.' % ', '.join(veri['fiyat_eksik'])
    sayfa(ws, 'Temizlik Malzemesi Tüketimi', basliklar, [tuple(x) for x in satirlar], olculer, 3, not_metni, para)

    if fiyatli:
        w0 = wb.create_sheet('Şube Tutarı')
        sayfa(w0, 'Şubelere göre aylık tutar', ['Şube', 'Durum', 'Tutar (TL)'],
              [(c['sube'].ad, 'Tamam' if c['tam'] else 'Sayım eksik', c['tutar']) for c in veri['subeler']]
              + [('TOPLAM', '', veri['genel_tutar'])], [34, 16, 16], 3,
              'Yalnızca ilk ve son sayımı girilmiş şubelerin tutarı hesaplanır.', (3,))

    if gorunum == 'aylik' and len(veri['subeler']) > 1:
        w2 = wb.create_sheet('Şube Kırılımı')
        bas = ['Ürün', 'Birim'] + [c['sube'].ad for c in veri['subeler']]
        sat = [(u.ad, u.birim) + tuple(h) for u, h in sube_kirilimi(veri)]
        if fiyatli:
            sat.append(('Toplam tutar (TL)', '') + tuple(c['tutar'] for c in veri['subeler']))
        sayfa(w2, 'Şubelere göre kullanım', bas, sat, [46, 10] + [14] * len(veri['subeler']), 3,
              'Boş hücre: o şubenin ilk veya son sayımı henüz girilmemiş.')
    elif gorunum in ('haftalik', 'gunluk'):
        parcalar = _parcalar(veri, gorunum)
        ad = 'Haftalık' if gorunum == 'haftalik' else 'Günlük'
        w2 = wb.create_sheet('%s İlave' % ad)
        sayfa(w2, '%s ilave (gelen sevkiyat + düzeltme)' % ad, ['Ürün', 'Birim'] + [p['etiket'] for p in parcalar],
              [(r['urun'].ad, r['urun'].birim) + tuple(parca_toplam(r['gun_ilave'], p) for p in parcalar)
               for r in veri['toplam']], [46, 10] + [10 if gorunum == 'gunluk' else 13] * len(parcalar), 3)
        w3 = wb.create_sheet('%s Tüketim (tahmini)' % ad)
        sayfa(w3, '%s tüketim — tahmini' % ad, ['Ürün', 'Birim'] + [p['etiket'] for p in parcalar],
              [(r['urun'].ad, r['urun'].birim) + tuple(parca_toplam(r['gun_tuketim'], p) if r['gun_tuketim'] else None
                                                      for p in parcalar) for r in veri['toplam']],
              [46, 10] + [10 if gorunum == 'gunluk' else 13] * len(parcalar), 3,
              'Tüketim yalnızca iki sayım arasında bilinir; bu tablo aylık kullanımın günlere eşit dağıtılmış tahminidir.')
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def pdf_bytes(veri, secili, gorunum):
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from .pdf_letterhead import build_pdf
    from .zayi_rapor import _pdf_font

    FONT, FONTB = _pdf_font()
    BRAND = colors.HexColor('#162AA3')
    ZEBRA = colors.HexColor('#F4F6FB')
    LINE = colors.HexColor('#E3E6EF')
    MUTED = colors.HexColor('#6B7280')
    genis = gorunum in ('haftalik', 'gunluk') or (gorunum == 'aylik' and len(veri['subeler']) > 1)
    sayfa_boyu = landscape(A4) if genis else A4
    LEFT = RIGHT = 12 * mm
    W = sayfa_boyu[0] - LEFT - RIGHT
    kucuk = 6.2 if gorunum == 'gunluk' else 7.6
    st_baslik = ParagraphStyle('b', fontName=FONTB, fontSize=14, textColor=BRAND, leading=18)
    st_alt = ParagraphStyle('a', fontName=FONT, fontSize=9.5, textColor=MUTED, leading=14)
    st_sb = ParagraphStyle('sb', fontName=FONTB, fontSize=11, textColor=BRAND, leading=15)
    st_c = ParagraphStyle('c', fontName=FONT, fontSize=kucuk, leading=kucuk + 2.4)
    st_cw = ParagraphStyle('cw', fontName=FONTB, fontSize=kucuk, leading=kucuk + 2.4, textColor=colors.white)
    st_not = ParagraphStyle('n', fontName=FONT, fontSize=7.4, textColor=MUTED, leading=10)

    def P(t, st=st_c):
        return Paragraph(escape('' if t is None else str(t)), st)

    def sayi(v):
        return '—' if v is None else sayi_yaz(v)

    def tablo(rows, kolonlar, sag_ilk=2):
        t = Table(rows, colWidths=kolonlar, repeatRows=1)
        stil = [('BACKGROUND', (0, 0), (-1, 0), BRAND), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ZEBRA]),
                ('GRID', (0, 0), (-1, -1), 0.3, LINE), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
                ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3)]
        stil += [('ALIGN', (c, 0), (c, -1), 'RIGHT') for c in range(sag_ilk, len(kolonlar))]
        t.setStyle(TableStyle(stil))
        return t

    el = [Paragraph('Temizlik Malzemesi Tüketimi', st_baslik), Paragraph(escape(_etiket(veri, secili, gorunum)), st_alt),
          Paragraph('Şube: %d / %d tamamlandı (ilk ve son sayım girilmiş)' % (veri['tam_sube'], len(veri['subeler'])), st_alt),
          Spacer(1, 6)]
    fiyatli = veri.get('fiyatli', False)
    basliklar = ['Ürün', 'Birim', 'İlk stok', 'İlave', 'Düzeltme', 'Son stok', 'Kullanım', 'Kullanım (hacim)']
    if fiyatli:
        basliklar += ['Birim fiyat', 'Tutar (TL)']
    rows = [[P(h, st_cw) for h in basliklar]]
    for r in veri['toplam']:
        satir = [P(r['urun'].ad), P(r['urun'].birim), P(sayi(r['ilk'])), P(sayi(r['ilave'])),
                 P(sayi(r['duzeltme'])), P(sayi(r['son'])), P(sayi(r['kullanim'])),
                 P(hacim_karsiligi(r['kullanim'], r['urun']))]
        if fiyatli:
            satir += [P(para_yaz(r['adet_fiyat'])), P(para_yaz(r['tutar']))]
        rows.append(satir)
    if fiyatli:
        rows.append([P('TOPLAM TUTAR', st_cw if False else st_c)] + [P('')] * 8 + [P(para_yaz(veri['genel_tutar']))])
        oran = [.22, .06, .07, .07, .07, .07, .09, .12, .10, .13]
    else:
        oran = [.3, .08, .09, .09, .09, .09, .11, .15]
    el.append(tablo(rows, [W * o for o in oran]))
    el.append(Spacer(1, 8))
    if fiyatli:
        el.append(Paragraph('Şubelere göre aylık tutar', st_sb))
        rows = [[P('Şube', st_cw), P('Durum', st_cw), P('Tutar (TL)', st_cw)]]
        for c in veri['subeler']:
            rows.append([P(c['sube'].ad), P('Tamam' if c['tam'] else 'Sayım eksik'), P(para_yaz(c['tutar']))])
        rows.append([P('TOPLAM'), P(''), P(para_yaz(veri['genel_tutar']))])
        el.append(tablo(rows, [W * .5, W * .25, W * .25], sag_ilk=2))
        if veri['fiyat_eksik']:
            el.append(Paragraph('Fiyatı girilmemiş ürünler toplama dahil değil: ' + escape(', '.join(veri['fiyat_eksik'])), st_not))
        el.append(Spacer(1, 8))

    if gorunum == 'aylik' and len(veri['subeler']) > 1:
        n = len(veri['subeler'])
        el.append(Paragraph('Şubelere göre kullanım', st_sb))
        rows = [[P('Ürün', st_cw)] + [P(c['sube'].ad, st_cw) for c in veri['subeler']]]
        for u, h in sube_kirilimi(veri):
            rows.append([P(u.ad)] + [P(sayi(x)) for x in h])
        if fiyatli:
            rows.append([P('Toplam tutar (TL)')] + [P(para_yaz(c['tutar'])) for c in veri['subeler']])
        el.append(tablo(rows, [W * .26] + [W * .74 / n] * n, sag_ilk=1))
    elif gorunum in ('haftalik', 'gunluk'):
        parcalar = _parcalar(veri, gorunum)
        n = len(parcalar)
        for baslik, anahtar, tahmin in (('İlave (gelen sevkiyat + düzeltme)', 'gun_ilave', False),
                                        ('Tüketim — tahmini', 'gun_tuketim', True)):
            el.append(Paragraph(baslik, st_sb))
            rows = [[P('Ürün', st_cw)] + [P(p['etiket'] if gorunum == 'haftalik' else p['ad'], st_cw) for p in parcalar]]
            for r in veri['toplam']:
                rows.append([P(r['urun'].ad)] + [
                    P('—' if (tahmin and not r['gun_tuketim']) else sayi(parca_toplam(r[anahtar], p))) for p in parcalar])
            el.append(tablo(rows, [W * .22] + [W * .78 / n] * n, sag_ilk=1))
            el.append(Spacer(1, 8))
    el.append(Spacer(1, 4))
    el.append(Paragraph('Kullanım = İlk stok + İlave + Düzeltme − Son stok. İlave, çıkışı onaylanmış sevkiyatlardan alınır. '
                        'Hafta ve gün tüketimi, iki sayım arasındaki toplam kullanımın eşit dağıtılmış tahminidir.', st_not))
    buf = io.BytesIO()
    build_pdf(buf, el, pagesize=sayfa_boyu, left_margin=LEFT, right_margin=RIGHT, font=FONT,
              title='Temizlik Malzemesi Tüketimi')
    return buf.getvalue()
