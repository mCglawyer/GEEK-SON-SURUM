from django.utils import timezone
from .models import Personel, Bildirim, Kalibrasyon, Rol


def bildirim_ctx(request):
    u = getattr(request, 'user', None)
    if not u or not getattr(u, 'is_authenticated', False):
        return {}
    try:
        p = Personel.objects.filter(user=u).first()
        if not p:
            return {}
        qs = Bildirim.objects.filter(alici=p)
        return {
            'bildirim_adet': qs.filter(okundu=False).count(),
            'bildirim_son': list(qs[:8]),
        }
    except Exception:
        return {}


KALIBRASYON_PENCERELERI = [(8, 0, 8, 30), (12, 0, 12, 30), (14, 0, 14, 30), (17, 0, 17, 30), (21, 0, 21, 30)]


def kalibrasyon_uyari_ctx(request):
    u = getattr(request, 'user', None)
    if not u or not getattr(u, 'is_authenticated', False):
        return {}
    try:
        p = Personel.objects.filter(user=u).first()
        if not p or p.rol != Rol.MUDUR:
            return {}
        now = timezone.localtime()
        pencere = None
        for sh, sm, eh, em in KALIBRASYON_PENCERELERI:
            bas = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            bit = now.replace(hour=eh, minute=em, second=59, microsecond=999999)
            if bas <= now <= bit:
                pencere = (bas, bit)
                break
        if not pencere:
            return {}
        bas, bit = pencere
        subeler = list(p.sorumlu_subeler.all())
        if not subeler:
            return {}
        yapan_ids = set(Kalibrasyon.objects.filter(
            sube__in=subeler, olusturma__gte=bas, olusturma__lte=bit
        ).values_list('sube_id', flat=True))
        eksik = [s.ad for s in subeler if s.id not in yapan_ids]
        if eksik:
            return {'kalibrasyon_uyari': eksik,
                    'kalibrasyon_pencere': '%02d:%02d-%02d:%02d' % (bas.hour, bas.minute, bit.hour, bit.minute)}
        return {}
    except Exception:
        return {}


def egitim_ctx(request):
    u = getattr(request, 'user', None)
    if not u or not getattr(u, 'is_authenticated', False):
        return {}
    try:
        from .models import EgitimAyar, Personel
        a = EgitimAyar.objects.first()
        if not a or not a.acik:
            return {'egitim_acik': False}
        acik_ids = set(a.acik_subeler.values_list('id', flat=True))
        if not acik_ids:
            return {'egitim_acik': True}
        p = Personel.objects.filter(user=u).only('sube').first()
        if p is None:
            return {'egitim_acik': True}
        return {'egitim_acik': (p.sube_id in acik_ids)}
    except Exception:
        return {}
