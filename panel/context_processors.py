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


def sube_secici_ctx(request):
    """Üst bardaki global şube seçici için: kullanıcının şubeleri + seçili şube."""
    u = getattr(request, 'user', None)
    if not u or not getattr(u, 'is_authenticated', False):
        return {}
    try:
        from .models import Personel, Sube, Rol
        p = Personel.objects.filter(user=u).only('rol', 'id').first()
        if p is None or p.rol not in (Rol.GENEL_MUDUR, Rol.MUDUR, Rol.OPERATOR, Rol.YATIRIMCI):
            return {}
        if p.rol == Rol.MUDUR:
            subeler = list(p.sorumlu_subeler.order_by('ad'))
        else:
            subeler = list(Sube.objects.order_by('ad'))
        if len(subeler) < 2:
            return {}
        sid = str(request.session.get('sel_sube_id') or '')
        if not any(str(s.id) == sid for s in subeler):
            varsayilan = next((s for s in subeler if not s.depo_mu), subeler[0])
            sid = str(varsayilan.id)
        return {'ust_subeler': subeler, 'ust_secili_sube_id': sid}
    except Exception:
        return {}


def acilis_ctx(request):
    """Girişten sonraki ilk sayfada bir kez alıntı ekranı gösterilmesini sağlar.
    _kod_giris/_sifre_giris başarılı girişte session'a bayrak koyar; burada
    okunup hemen tüketilir (pop), böylece sayfa yenilense/gezinilse dahi
    tekrar çıkmaz — sadece asıl giriş anında görünür."""
    try:
        if request.session.pop('acilis_goster', False):
            return {'acilis_goster': True}
    except Exception:
        pass
    return {}
