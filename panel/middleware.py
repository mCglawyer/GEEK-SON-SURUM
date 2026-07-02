from django.shortcuts import redirect


class EgitimKapiMiddleware:
    """Sınavı geçmemiş barista/şef, sistem açıkken eğitim sayfasına yönlendirilir."""

    IZINLI_PREFIX = ('/egitim', '/static', '/media', '/admin')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        red = self._gate(request)
        if red is not None:
            return red
        return self.get_response(request)

    def _gate(self, request):
        try:
            if request.method != 'GET':
                return None
            u = getattr(request, 'user', None)
            if not u or not u.is_authenticated:
                return None
            path = request.path or '/'
            for p in self.IZINLI_PREFIX:
                if path.startswith(p):
                    return None
            from .models import Personel, EgitimDurum, EgitimAyar, EgitimDokuman, EgitimSoru, Rol
            from django.db.models import Q
            ayar = EgitimAyar.objects.first()
            if not (ayar and ayar.acik):
                return None
            personel = Personel.objects.filter(user=u).first()
            if personel is None or personel.rol not in (Rol.PERSONEL, Rol.SEF):
                return None
            # Şube-bazlı: kişinin şubesi açık değilse kilitleme
            acik_ids = set(ayar.acik_subeler.values_list('id', flat=True))
            if acik_ids and personel.sube_id not in acik_ids:
                return None
            durum = EgitimDurum.objects.filter(personel=personel).first()
            if durum and durum.tamamlandi:
                return None
            # Güvenlik ağı: kişinin şubesine uygun içerik hazır değilse kilitleme
            sube_dok = EgitimDokuman.objects.filter(aktif=True).filter(Q(sube__isnull=True) | Q(sube=personel.sube))
            if not sube_dok.exists():
                return None
            sube_soru = EgitimSoru.objects.filter(aktif=True).filter(Q(sube__isnull=True) | Q(sube=personel.sube))
            if sube_soru.count() < 10:
                return None
            return redirect('egitim')
        except Exception:
            return None
