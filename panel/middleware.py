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
            ayar = EgitimAyar.objects.first()
            if not (ayar and ayar.acik):
                return None
            personel = Personel.objects.filter(user=u).first()
            if personel is None or personel.rol not in (Rol.PERSONEL, Rol.SEF):
                return None
            durum = EgitimDurum.objects.filter(personel=personel).first()
            if durum and durum.tamamlandi:
                return None
            # Güvenlik ağı: içerik hazır değilse kilitleme
            if not EgitimDokuman.objects.filter(aktif=True).exists():
                return None
            if EgitimSoru.objects.filter(aktif=True).count() < 10:
                return None
            return redirect('egitim')
        except Exception:
            return None
