"""Bar tüketim & maliyet (şube × ay × ürün).

Mantık
  Şef her ayın SON GÜNÜ stok sayımı girer (StokSayim). O sayım hem o ayın KAPANIŞ stoğu hem de bir sonraki ayın
  AÇILIŞ stoğudur; şefe ek iş çıkmaz.
      Kullanım (ay M) = Açılış (M-1 sayımı) + Gelen (ay M içinde çıkışı onaylanmış sevkiyatlar) − Kapanış (M sayımı)
  Gelen mal sevkiyat kayıtlarından kendiliğinden gelir; sayım biriminde (ml, gr, adet) ifade edilmesi için
  StokUrun.sevkiyat_urun + sevkiyat_carpan eşlemesi kullanılır.

Maliyet (ağırlıklı ortalama)
  Fiyat, sevkiyat kataloğundaki ürünün TABAN BİRİMİ (1 adet / şişe / paket / kg) başınadır ve tarihlidir.
  Ortalama birim maliyet = (açılış stoğu × ay başı fiyatı + Σ gelen_i × teslim günü fiyatı) / (açılış + Σ gelen_i)
  Maliyet = kullanım × ortalama birim maliyet. Böylece ay ortası fiyat değişikliği, değişiklikten önce ve sonra gelen
  malın payına göre doğru yansır.
  Fiyat önceliği: şubeye özel fiyat > şubenin fiyat grubu (Merkez / Franchise). Fiyat kimin görebileceği görünürlük
  kurallarıyla (fiyat_gorur_sube) ayrıca sınırlanır.

Sınırlar (ekranlarda da belirtilir)
  * Kullanım içinde fire de vardır; stok sayımı ikisini ayıramaz.
  * Kullanım yalnızca iki sayım arasında bilinir.
"""
import datetime
import difflib
import re
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import DateTimeField
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import (Rol, SevkiyatBirim, SevkiyatDurumu, SevkiyatKalem, StokSayim, StokUrun, Sube, TuketimAyar,
                     TuketimFiyat, Urun)
from .sevkiyat_analiz import ay_etiketi, ay_komsulari, ay_oku, sayi_yaz  # noqa: F401  (ekranlar buradan alır)
from .temizlik import _gelen_miktar, ay_sonu, para_yaz, sade  # noqa: F401

_SIFIR = Decimal('0')
_GELEN_DURUMLAR = (SevkiyatDurumu.ONAYLANDI, SevkiyatDurumu.TESLIM)

# Yetki
YONETIM_ROLLERI = (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.SATIN_ALMA)            # ayar, eşleme, fiyat yönetimi
TUM_FIYAT_ROLLERI = (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI, Rol.SATIN_ALMA)   # tüm şubelerin fiyatını görür
RAPOR_ROLLERI = (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI, Rol.SATIN_ALMA, Rol.MUDUR, Rol.SEF, Rol.MAGAZA_MUDURU)


# ----------------------------------------------------------------------------- yetki / kapsam
def _depo_disi():
    return Sube.objects.filter(depo_mu=False).order_by('ad')


def rapor_subeleri(personel):
    """Raporda görebileceği şubeler. Bölge müdürü yalnız sorumlu olduğu, şef/mağaza müdürü yalnız kendi şubesini görür."""
    if personel is None or personel.rol not in RAPOR_ROLLERI:
        return []
    if personel.rol in TUM_FIYAT_ROLLERI:
        return list(_depo_disi())
    if personel.rol == Rol.MUDUR:
        return list(personel.sorumlu_subeler.filter(depo_mu=False).order_by('ad'))
    if personel.rol == Rol.MAGAZA_MUDURU and personel.sorumlu_subeler.exists():
        return list(personel.sorumlu_subeler.filter(depo_mu=False).order_by('ad'))
    return [personel.sube] if personel.sube_id and not personel.sube.depo_mu else []


def fiyat_yonetebilir(personel):
    return personel is not None and personel.rol in YONETIM_ROLLERI


def erisebilir(personel, ayar):
    """Sistem kapalıyken yalnızca yönetim (GM, Operatör, Satın Alma) içeri girer."""
    return bool(ayar.aktif) or (personel is not None and personel.rol in YONETIM_ROLLERI)


def baslamamis(ayar, ay_ilk):
    """İlk sayım ayından önceki aylar için kullanım hesaplanmaz."""
    return bool(ayar.baslangic and ay_ilk <= ayar.baslangic.replace(day=1))


# ----------------------------------------------------------------------------- dönem
def onceki_ay(ay_ilk):
    return ay_komsulari(ay_ilk)[0]


def donem(ay_ilk, ayar):
    """(bas, bit): gelen mal günü g için  bas < g <= bit.  Ayın son günü kuralı ayara göre."""
    kay = datetime.timedelta(days=0 if ayar.son_gun_ayda else 1)
    return ay_sonu(onceki_ay(ay_ilk)) - kay, ay_sonu(ay_ilk) - kay


# ----------------------------------------------------------------------------- sayı
def taban_miktar(k, miktar, birim):
    """Sevkiyat kalemindeki miktarı ürünün TABAN birimine (adet/şişe/paket/kg) çevirir (koli → × içerik)."""
    u = k.urun
    if u is not None and u.ust_birim and u.ust_birim != u.birim and birim == u.ust_birim:
        return miktar * Decimal(k.koli_icerigi or u.koli_icerigi or 1)
    if birim == SevkiyatBirim.KOLI:
        return miktar * Decimal(k.koli_icerigi or (u.koli_icerigi if u else 1) or 1)
    return miktar


def varsayilan_carpan(stok_urun, sevkiyat_urun):
    """1 sevkiyat taban birimi = kaç sayım birimi?  KG/LİTRE ile gelip gr/ml sayılıyorsa 1000; aksi hâlde kapalı kutu içeriği."""
    if sevkiyat_urun is not None and sevkiyat_urun.birim in (SevkiyatBirim.KG, SevkiyatBirim.LITRE):
        return Decimal('1000')
    return Decimal(stok_urun.kapali_icerik or 1)


def carpan(stok_urun):
    if stok_urun.sevkiyat_carpan:
        return Decimal(stok_urun.sevkiyat_carpan)
    return varsayilan_carpan(stok_urun, stok_urun.sevkiyat_urun)


def _yuvarla(d, n='0.01'):
    return None if d is None else Decimal(d).quantize(Decimal(n), rounding=ROUND_HALF_UP)


# ----------------------------------------------------------------------------- fiyat
class FiyatDefteri:
    """Tüm tarihli fiyatları bir kez okur; (ürün, şube, gün) için fiyat bulur."""

    def __init__(self):
        self.satirlar = {}
        for f in TuketimFiyat.objects.order_by('gecerli', 'id'):
            self.satirlar.setdefault(f.urun_id, []).append(f)

    def bul(self, urun_id, sube, gun):
        satirlar = self.satirlar.get(urun_id)
        if not satirlar or sube is None:
            return None
        sube_f = [f for f in satirlar if f.sube_id == sube.id]
        grup_f = [f for f in satirlar if f.sube_id is None and f.grup == sube.fiyat_grubu]
        for havuz in (sube_f, grup_f):
            gecen = [f for f in havuz if f.gecerli <= gun]
            if gecen:
                return gecen[-1].fiyat
        kalan = sorted(sube_f + grup_f, key=lambda f: f.gecerli)      # henüz geçerli olmayan en eski fiyatı geriye uygula
        return kalan[0].fiyat if kalan else None


# ----------------------------------------------------------------------------- hesap
def _sayim_haritasi(sayim):
    """urun_id -> toplam (sayım birimi). Sayımda olmayan kalem 0 sayılır (şef sıfırları kaydetmez)."""
    cikti = {}
    ek = _SIFIR
    for k in sayim.kalemler.all():
        if k.urun_id is None:
            ek += k.toplam
        else:
            cikti[k.urun_id] = cikti.get(k.urun_id, _SIFIR) + k.toplam
    return cikti, ek


def _sevk_kalemleri(sube_ids, bas, bit):
    tz = timezone.get_current_timezone()
    ilk = timezone.make_aware(datetime.datetime.combine(bas + datetime.timedelta(days=1), datetime.time.min), tz)
    son = timezone.make_aware(datetime.datetime.combine(bit + datetime.timedelta(days=1), datetime.time.min), tz)
    return (SevkiyatKalem.objects
            .filter(talep__sube_id__in=sube_ids, talep__durum__in=_GELEN_DURUMLAR)
            .annotate(_eff=Coalesce('talep__onay_tarih', 'talep__sevkiyat_tarih', 'talep__olusturma',
                                    output_field=DateTimeField()))
            .filter(_eff__gte=ilk, _eff__lt=son)
            .select_related('talep', 'urun'))


def hesapla(subeler, ay_ilk, fiyatli=False, ayar=None, defter=None):
    """Seçili şubeler için ay verisi.

    subeler : [ {sube, durum, satirlar, tutar, ...} ]   durum: tam | sayim_bekleniyor | acilis_yok | baslamadi
    satır   : {urun, ilk, gelen, son, kullanim, kullanim_taban, birim_maliyet, tutar, uyari}
    toplam  : ürün bazında tüm şubelerin toplamı (sayım biriminde)
    eslesmeyen : bu dönemde gelen ama sayım kataloğuna bağlanamayan sevkiyat ürünleri
    """
    ayar = ayar or TuketimAyar.al()
    ids = [s.id for s in subeler]
    bas, bit = donem(ay_ilk, ayar)
    oncesi = onceki_ay(ay_ilk)
    urunler = list(StokUrun.objects.select_related('sevkiyat_urun').order_by('sira', 'ad'))
    esle_urun = {u.sevkiyat_urun_id: u for u in urunler if u.sevkiyat_urun_id}
    esle_ad = {sade(u.ad): u for u in urunler}
    defter = defter or (FiyatDefteri() if fiyatli else None)

    sayimlar = {}
    for sy in StokSayim.objects.filter(sube_id__in=ids, ay__in=[ay_ilk, oncesi]).prefetch_related('kalemler'):
        sayimlar[(sy.sube_id, sy.ay)] = (sy,) + _sayim_haritasi(sy)

    gelenler = {}                  # (sube_id, stok_urun_id) -> [(gun, taban_miktar)]
    eslesmeyen = {}
    if ids and not baslamamis(ayar, ay_ilk):
        for k in _sevk_kalemleri(ids, bas, bit):
            gun = timezone.localtime(k._eff).date()
            if not (bas < gun <= bit):
                continue
            su = esle_urun.get(k.urun_id) or esle_ad.get(sade(k.urun_ad or (k.urun.ad if k.urun_id else '')))
            m, b = _gelen_miktar(k)
            taban = taban_miktar(k, m, b)
            if su is None:
                if (k.form or '') != 'TEMIZLIK':
                    ad = (k.urun_ad or '—').strip()
                    e = eslesmeyen.setdefault(sade(ad), {'ad': ad, 'miktar': _SIFIR, 'birim': k.urun.birim if k.urun_id else ''})
                    e['miktar'] += taban
                continue
            gelenler.setdefault((k.talep.sube_id, su.id), []).append((gun, taban))

    cikti = []
    for s in subeler:
        son = sayimlar.get((s.id, ay_ilk))
        acilis = sayimlar.get((s.id, oncesi))
        if baslamamis(ayar, ay_ilk):
            durum = 'baslamadi'
        elif acilis is None:
            durum = 'acilis_yok'
        elif son is None:
            durum = 'sayim_bekleniyor'
        else:
            durum = 'tam'
        satirlar = []
        for u in urunler:
            c = carpan(u)
            ilk_v = acilis[1].get(u.id, _SIFIR) if acilis else None
            son_v = son[1].get(u.id, _SIFIR) if son else None
            gel = gelenler.get((s.id, u.id), [])
            gelen_t = sum((m for _, m in gel), _SIFIR)                 # taban birim
            gelen_s = gelen_t * c                                       # sayım birimi
            kullanim = (ilk_v + gelen_s - son_v) if durum == 'tam' else None
            if not u.aktif and not (gelen_t or ilk_v or son_v):
                continue
            if not (gelen_t or ilk_v or son_v):
                continue                                                # bu şubede hiç hareketi olmayan ürünü gösterme
            satir = {'urun': u, 'ilk': ilk_v, 'gelen': gelen_s, 'gelen_taban': gelen_t, 'son': son_v,
                     'kullanim': kullanim, 'kullanim_taban': (kullanim / c) if kullanim is not None else None,
                     'carpan': c, 'uyari': ''}
            if kullanim is not None and kullanim < 0:
                satir['uyari'] = 'Kullanım eksi çıktı: sayım ya da gelen mal kaydını kontrol edin.'
            if fiyatli:
                _maliyet_ekle(satir, s, u, c, ilk_v, gel, bas, defter)
            satirlar.append(satir)
        cikti.append({'sube': s, 'durum': durum, 'ilk': acilis[0] if acilis else None, 'son': son[0] if son else None,
                      'satirlar': satirlar, 'ek_stok': son[2] if son else None})
    toplam = _toplam_satirlari(cikti, urunler, fiyatli)
    sonuc = {'ay': ay_ilk, 'etiket': ay_etiketi(ay_ilk), 'bas': bas, 'bit': bit, 'subeler': cikti, 'toplam': toplam,
             'tam_sube': sum(1 for c in cikti if c['durum'] == 'tam'),
             'eslesmeyen': sorted(eslesmeyen.values(), key=lambda e: e['ad']), 'fiyatli': fiyatli}
    if fiyatli:
        for c in cikti:
            c['tutar'] = (sum((r['tutar'] for r in c['satirlar'] if r['tutar'] is not None), _SIFIR)
                          if c['durum'] == 'tam' else None)
            c['fiyat_eksik'] = sorted({r['urun'].ad for r in c['satirlar']
                                       if r.get('fiyat_eksik') and r['kullanim'] not in (None, _SIFIR)})
        sonuc['genel_tutar'] = sum((c['tutar'] for c in cikti if c['tutar'] is not None), _SIFIR)
        sonuc['fiyat_eksik'] = sorted({a for c in cikti for a in c['fiyat_eksik']})
    return sonuc


def _maliyet_ekle(satir, sube, urun, c, ilk_v, gel, bas, defter):
    """Ağırlıklı ortalama birim maliyet ve tutar (taban birim başına TL)."""
    sevk = urun.sevkiyat_urun_id
    satir['birim_maliyet'] = None
    satir['tutar'] = None
    satir['fiyat_eksik'] = False
    if not sevk:
        satir['fiyat_eksik'] = True
        return
    ilk_taban = (ilk_v / c) if ilk_v else _SIFIR
    parcalar = []                                  # (taban miktar, fiyat)
    if ilk_taban:
        parcalar.append((ilk_taban, defter.bul(sevk, sube, bas + datetime.timedelta(days=1))))
    for gun, m in gel:
        parcalar.append((m, defter.bul(sevk, sube, gun)))
    if any(f is None for _, f in parcalar):
        satir['fiyat_eksik'] = True
        return
    toplam_m = sum((m for m, _ in parcalar), _SIFIR)
    if toplam_m > 0:
        ort = sum((m * f for m, f in parcalar), _SIFIR) / toplam_m
    else:
        ort = defter.bul(sevk, sube, bas + datetime.timedelta(days=1))
        if ort is None:
            satir['fiyat_eksik'] = True
            return
    satir['birim_maliyet'] = _yuvarla(ort, '0.0001')
    if satir['kullanim_taban'] is not None:
        satir['tutar'] = _yuvarla(satir['kullanim_taban'] * ort)


def _toplam_satirlari(cikti, urunler, fiyatli):
    sonuc = []
    for u in urunler:
        satir = {'urun': u, 'ilk': None, 'gelen': _SIFIR, 'gelen_taban': _SIFIR, 'son': None, 'kullanim': None,
                 'kullanim_taban': None, 'carpan': carpan(u), 'tutar': None, 'birim_maliyet': None, 'uyari': ''}
        var = False
        tutarlar = []
        for c in cikti:
            r = next((x for x in c['satirlar'] if x['urun'].id == u.id), None)
            if r is None:
                continue
            var = True
            satir['gelen'] += r['gelen']
            satir['gelen_taban'] += r['gelen_taban']
            for alan in ('ilk', 'son', 'kullanim', 'kullanim_taban'):
                if r[alan] is not None:
                    satir[alan] = (satir[alan] or _SIFIR) + r[alan]
            if fiyatli and r.get('tutar') is not None:
                tutarlar.append(r['tutar'])
        if var:
            if fiyatli and tutarlar:
                satir['tutar'] = sum(tutarlar, _SIFIR)
                if satir['kullanim_taban'] and satir['kullanim_taban'] > 0:
                    satir['birim_maliyet'] = _yuvarla(satir['tutar'] / satir['kullanim_taban'], '0.0001')
            sonuc.append(satir)
    return sonuc


# ----------------------------------------------------------------------------- grafik serisi
def aylik_seri(subeler, bitis_ay, adet=6, ayar=None):
    """Son `adet` ayın şube bazlı maliyet toplamı (sütun grafik için). Hesaplanamayan ay None."""
    ayar = ayar or TuketimAyar.al()
    defter = FiyatDefteri()
    aylar = []
    a = bitis_ay
    for _ in range(adet):
        aylar.append(a)
        a = onceki_ay(a)
    aylar.reverse()
    seri = {s.id: [] for s in subeler}
    toplam = []
    for ay in aylar:
        v = hesapla(subeler, ay, fiyatli=True, ayar=ayar, defter=defter)
        t = _SIFIR
        var = False
        for c in v['subeler']:
            seri[c['sube'].id].append(c['tutar'])
            if c['tutar'] is not None:
                t += c['tutar']
                var = True
        toplam.append(t if var else None)
    return {'aylar': aylar, 'etiketler': [ay_etiketi(a) for a in aylar], 'seri': seri, 'toplam': toplam}


# ----------------------------------------------------------------------------- eşleme önerisi
_PARANTEZ = re.compile(r'\([^)]*\)')


def _anahtar(ad):
    t = sade(_PARANTEZ.sub(' ', str(ad or '')))
    t = re.sub(r'\b(ml|lt|kg|gr|gram|adet|\d+)\b', ' ', t)
    return ' '.join(t.split())


def esleme_oner(stok_urunler, sevkiyat_urunler, esik=0.78):
    """StokUrun.id -> (Urun, güven) önerisi. Ad benzerliği (parantez içindeki gramaj/ölçü yok sayılır)."""
    adaylar = [(_anahtar(u.ad), u) for u in sevkiyat_urunler]
    oneri = {}
    for su in stok_urunler:
        a = _anahtar(su.ad)
        en_iyi, skor = None, 0.0
        for k, u in adaylar:
            if not k or not a:
                continue
            r = 1.0 if k == a else difflib.SequenceMatcher(None, a, k).ratio()
            if r > skor:
                en_iyi, skor = u, r
        if en_iyi is not None and skor >= esik:
            oneri[su.id] = (en_iyi, round(skor, 2))
    return oneri
