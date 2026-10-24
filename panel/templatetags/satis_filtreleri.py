from django import template
from ..satis_cikti import tl as _tl, adet as _adet

register = template.Library()
register.filter('tlf', lambda v: _tl(v) + ' ₺')
register.filter('adetf', _adet)
register.filter('sayif', lambda v: _tl(v))
