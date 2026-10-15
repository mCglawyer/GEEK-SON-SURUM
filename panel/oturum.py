"""Bölge müdürlerinin uygulamaya giriş takibi.

Sayılan olay iki türlüdür:
  * giris  — şifre/kodla oturum açma
  * acilis — oturum zaten açıkken (telefonda uygulama açık kalır) 30 dakikadan uzun aradan sonra uygulamaya dönüş
Aynı kullanım içindeki sayfa gezintileri sayılmaz; böylece "günde kaç kez uygulamaya girdi" gerçeğe yakın çıkar.
"""
import time

from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in

ARALIK_SN = 30 * 60          # bu kadar sessizlikten sonraki ilk sayfa = yeni açılış
YAZMA_ARALIGI_SN = 60        # oturuma son görülmeyi en çok dakikada bir yaz (gereksiz DB yazımı olmasın)
_ATLA = ('/static', '/media', '/icons', '/sw.js', '/manifest', '/push', '/favicon', '/admin')


def _mudur_bilgisi(request):
    """Oturumda önbellekli: (mudur_mu, personel_id)."""
    s = request.session
    if '_izle_pid' not in s:
        from .models import Personel, Rol
        p = Personel.objects.filter(user=request.user).only('id', 'rol').first()
        s['_izle_pid'] = p.id if (p and p.rol == Rol.MUDUR) else 0
    return bool(s['_izle_pid']), s['_izle_pid']


def kayit_ekle(personel_id, tur):
    from .models import OturumKaydi
    OturumKaydi.objects.create(personel_id=personel_id, tur=tur)


@receiver(user_logged_in)
def girisi_kaydet(sender, request, user, **kw):
    try:
        if request is None or not hasattr(request, 'session'):
            return
        from .models import Personel, Rol
        p = Personel.objects.filter(user=user).only('id', 'rol').first()
        pid = p.id if (p and p.rol == Rol.MUDUR) else 0
        request.session['_izle_pid'] = pid
        if pid:
            kayit_ekle(pid, 'giris')
            request.session['_izle_son'] = time.time()
    except Exception:
        pass


class OturumIzlemeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        yanit = self.get_response(request)
        try:
            self._izle(request, yanit)
        except Exception:
            pass
        return yanit

    def _izle(self, request, yanit):
        if request.method != 'GET' or yanit.status_code >= 400:
            return
        u = getattr(request, 'user', None)
        if not u or not u.is_authenticated:
            return
        if request.path.startswith(_ATLA) or request.headers.get('X-Requested-With'):
            return
        if not (yanit.get('Content-Type') or '').startswith('text/html'):
            return
        mudur, pid = _mudur_bilgisi(request)
        if not mudur:
            return
        simdi = time.time()
        son = request.session.get('_izle_son', 0)
        if simdi - son > ARALIK_SN:
            kayit_ekle(pid, 'acilis')
        if simdi - son > YAZMA_ARALIGI_SN:
            request.session['_izle_son'] = simdi
