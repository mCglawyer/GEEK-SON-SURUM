"""Eski Temizlik modülünden kalan ortak yardımcılar (temizlik artık Tüketim & Maliyet içinde)."""
import calendar
from decimal import Decimal, ROUND_HALF_UP

from .models import SevkiyatDurumu
from .sevkiyat_analiz import sayi_yaz  # noqa: F401

_SIFIR = Decimal('0')
_GELEN_DURUMLAR = (SevkiyatDurumu.ONAYLANDI, SevkiyatDurumu.TESLIM)
_TR = str.maketrans({'İ': 'i', 'I': 'i', 'ı': 'i', 'Ç': 'c', 'ç': 'c', 'Ş': 's', 'ş': 's',
                     'Ğ': 'g', 'ğ': 'g', 'Ö': 'o', 'ö': 'o', 'Ü': 'u', 'ü': 'u'})


def sade(metin):
    return ' '.join(str(metin or '').translate(_TR).lower().split())


def ay_sonu(ay_ilk):
    return ay_ilk.replace(day=calendar.monthrange(ay_ilk.year, ay_ilk.month)[1])


def para_yaz(d):
    """1250.5 -> '1.250,50'"""
    if d is None:
        return '—'
    s = '{:,.2f}'.format(Decimal(d).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    return s.replace(',', '§').replace('.', ',').replace('§', '.')


def _gelen_miktar(k):
    if k.sevkiyat_miktar is not None:
        return k.sevkiyat_miktar, (k.sevkiyat_birim or k.istenen_birim)
    if k.satinalma_miktar is not None:
        return k.satinalma_miktar, (k.satinalma_birim or k.istenen_birim)
    return (k.istenen_miktar or _SIFIR), k.istenen_birim
