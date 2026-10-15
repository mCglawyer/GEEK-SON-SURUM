from django import template

from ..sevkiyat_analiz import sayi_yaz
from ..temizlik import hacim_karsiligi

register = template.Library()


@register.filter
def tzsayi(deger):
    """Decimal -> 1.250,5 ; None -> —"""
    return '—' if deger is None else sayi_yaz(deger)


@register.filter
def tzhacim(kullanim, urun):
    """Kullanımın hacim karşılığı: '≈ 6.200 ml' (kapasitesi yoksa boş)."""
    return hacim_karsiligi(kullanim, urun)
