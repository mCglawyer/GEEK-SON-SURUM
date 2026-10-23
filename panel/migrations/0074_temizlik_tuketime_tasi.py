"""Temizlik malzemelerini bar ile aynı yapıya (stok sayımı + tüketim & maliyet) taşır.

* Her TemizlikUrun -> StokUrun ('TEMİZLİK MALZEMELERİ' grubu), sevkiyat karşılığıyla birlikte.
* Ay sonu (SON) temizlik sayımları -> o ay/şube için VAR OLAN StokSayim'a kalem olarak eklenir. Stok sayımı yoksa
  oluşturulmaz (boş sayım, barın tüm ürünlerini 0 gösterirdi). Ay başı (ILK) sayımları da yalnız önceki ay sayımı
  varsa ve o ay temizlik SON kaydı yoksa eklenir.
* Fiyatlar (TemizlikFiyat) -> TuketimFiyat (adet başına, Merkez ve Franchise için aynı).
Eski Temizlik tabloları silinmez (kayıt olarak kalır).
"""
import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations

GRUP = 'TEMİZLİK MALZEMELERİ'
_TR = str.maketrans({'İ': 'i', 'I': 'i', 'ı': 'i', 'Ç': 'c', 'ç': 'c', 'Ş': 's', 'ş': 's',
                     'Ğ': 'g', 'ğ': 'g', 'Ö': 'o', 'ö': 'o', 'Ü': 'u', 'ü': 'u'})
_KG = {'KG': Decimal('1'), 'GR': Decimal('0.001')}
_LT = {'LT': Decimal('1'), 'ML': Decimal('0.001')}


def _sade(m):
    return ' '.join(str(m or '').translate(_TR).lower().split())


def _onceki(ay):
    return (ay - datetime.timedelta(days=1)).replace(day=1)


def _adet_fiyati(tu, fiyat, birim):
    if birim == 'ADET':
        return fiyat
    if not tu.hacim:
        return None
    tablo = _KG if birim == 'KG' else _LT
    if (tu.hacim_birim or '').upper() not in tablo:
        return None
    return (fiyat * tu.hacim * tablo[tu.hacim_birim.upper()]).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def ileri(apps, schema_editor):
    TemizlikUrun = apps.get_model('panel', 'TemizlikUrun')
    TemizlikSayim = apps.get_model('panel', 'TemizlikSayim')
    TemizlikFiyat = apps.get_model('panel', 'TemizlikFiyat')
    StokUrun = apps.get_model('panel', 'StokUrun')
    StokSayim = apps.get_model('panel', 'StokSayim')
    StokSayimKalem = apps.get_model('panel', 'StokSayimKalem')
    Urun = apps.get_model('panel', 'Urun')
    TuketimFiyat = apps.get_model('panel', 'TuketimFiyat')

    temizlik_urunleri = list(Urun.objects.filter(form='TEMIZLIK'))
    ada_gore = {_sade(u.ad): u for u in temizlik_urunleri}
    sira = 0
    for s in StokUrun.objects.order_by('-sira')[:1]:
        sira = s.sira
    harita = {}                                     # TemizlikUrun.id -> StokUrun
    sevk_harita = {}                                # TemizlikUrun.id -> Urun
    for tu in TemizlikUrun.objects.order_by('sira', 'ad'):
        sevk = tu.urun or ada_gore.get(_sade(tu.ad))
        sevk_harita[tu.id] = sevk
        mevcut = None
        if sevk is not None:
            mevcut = StokUrun.objects.filter(sevkiyat_urun=sevk).first()
        if mevcut is None:
            mevcut = StokUrun.objects.filter(ad=tu.ad[:200], kategori=GRUP).first()
        if mevcut is None:
            sira += 1
            icerik = tu.hacim if tu.hacim else Decimal('1')
            mevcut = StokUrun.objects.create(kategori=GRUP, ad=tu.ad[:200], kapali_icerik=icerik, acik_carpan=1,
                                             sevkiyat_urun=sevk, sevkiyat_carpan=icerik if sevk else None,
                                             sira=sira, aktif=tu.aktif)
        harita[tu.id] = mevcut

    def _tasi(sayim, ay):
        hedef = StokSayim.objects.filter(sube_id=sayim.sube_id, ay=ay).first()
        if hedef is None:
            return False
        var = set(StokSayimKalem.objects.filter(sayim=hedef).exclude(urun=None).values_list('urun_id', flat=True))
        for k in sayim.kalemler.all():
            su = harita.get(k.urun_id)
            if su is None or su.id in var or not k.miktar:
                continue
            StokSayimKalem.objects.create(sayim=hedef, urun=su, urun_ad=su.ad, kategori=GRUP,
                                          kapali_icerik=su.kapali_icerik, acik_carpan=su.acik_carpan,
                                          kapali_adet=k.miktar, acik_miktar=0)
        return True

    son_var = set()
    for sy in TemizlikSayim.objects.filter(tur='SON').prefetch_related('kalemler'):
        if _tasi(sy, sy.ay):
            son_var.add((sy.sube_id, sy.ay))
    for sy in TemizlikSayim.objects.filter(tur='ILK').prefetch_related('kalemler'):
        onceki = _onceki(sy.ay)
        if (sy.sube_id, onceki) not in son_var:
            _tasi(sy, onceki)

    for f in TemizlikFiyat.objects.select_related('urun').order_by('gecerli'):
        sevk = sevk_harita.get(f.urun_id)
        if sevk is None:
            continue
        fiyat = _adet_fiyati(f.urun, f.fiyat, f.birim)
        if fiyat is None:
            continue
        for grup in ('MERKEZ', 'FRANCHISE'):
            if not TuketimFiyat.objects.filter(urun=sevk, grup=grup, sube=None, gecerli=f.gecerli).exists():
                TuketimFiyat.objects.create(urun=sevk, grup=grup, sube=None, fiyat=fiyat, gecerli=f.gecerli,
                                            giren_ad='Temizlik fiyatından taşındı')


class Migration(migrations.Migration):
    dependencies = [('panel', '0073_denetim_foto_yetki')]
    operations = [migrations.RunPython(ileri, migrations.RunPython.noop)]
