from django import template

from ..sevkiyat_analiz import sayi_yaz

register = template.Library()


@register.filter
def tzsayi(deger):
    """Decimal -> 1.250,5 ; None -> —"""
    return '—' if deger is None else sayi_yaz(deger)
