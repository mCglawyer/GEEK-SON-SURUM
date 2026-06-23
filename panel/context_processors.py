from .models import Personel, Bildirim


def bildirim_ctx(request):
    """Her sayfada zil rozeti + son bildirimler için."""
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
