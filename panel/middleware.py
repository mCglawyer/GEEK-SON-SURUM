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


class RadyoKabukMiddleware:
    """Kalıcı Geek Radio kabuğu.

    Oturum açmış kişi panele tarayıcı sekmesinden (üst düzey gezinti) geldiğinde, sayfanın kendisi yerine
    küçük bir "kabuk" sayfası döner; asıl sayfa kabuğun içindeki iframe'de açılır. Radyo oynatıcısı kabukta
    yaşadığı için sayfalar arasında gezinirken müzik kesilmez. Kabuğun içindeki istekler (Sec-Fetch-Dest: iframe)
    normal sayfayı alır. Sec-Fetch-Dest göndermeyen eski tarayıcılar kabuk görmez, panel eskisi gibi çalışır.
    """

    # Kabuğa sarılmayan yollar: statikler, dosya/indirme uçları, herkese açık sayfalar, ayrı PWA'lar.
    ATLA_PREFIX = ('/static', '/media', '/admin', '/icons', '/push', '/bildirim/', '/academy',
                   '/degerlendirme/', '/mesai/qr/', '/mola/qr/', '/menu/', '/kvkk', '/gizlilik',
                   '/kullanim-kosullari', '/geek-kosu/skor')
    ATLA_ICERIR = ('/excel/', '/pdf/', '/indir/', '/belge/', '/veri/', '/rapor/indir')
    ATLA_TAM = ('/sw.js', '/manifest.webmanifest', '/favicon.ico')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        kabuk = self._kabuk(request)
        if kabuk is not None:
            return kabuk
        yanit = self.get_response(request)
        try:
            if request.method == 'GET' and 'text/html' in (yanit.get('Content-Type') or ''):
                from django.utils.cache import patch_vary_headers
                patch_vary_headers(yanit, ('Sec-Fetch-Dest',))
        except Exception:
            pass
        return yanit

    def _kabuk(self, request):
        try:
            from django.conf import settings
            if not getattr(settings, 'GEEK_KABUK', True) or request.method != 'GET':
                return None
            h = request.headers
            dest = h.get('Sec-Fetch-Dest')
            # Service worker üzerinden gelen sekme gezintisinde Sec-Fetch-Dest 'empty' görünür; hedefi X-Geek-Dest bildirir.
            sw_belge = dest == 'empty' and h.get('X-Geek-Dest') == 'document'
            if not (sw_belge or (dest == 'document' and h.get('Sec-Fetch-Mode') == 'navigate')):
                return None
            if request.GET.get('kabuksuz'):
                return None
            u = getattr(request, 'user', None)
            if not u or not u.is_authenticated:
                return None
            path = request.path or '/'
            if path in self.ATLA_TAM or path.startswith(self.ATLA_PREFIX) or any(x in path for x in self.ATLA_ICERIR):
                return None
            if '.' in path.rsplit('/', 1)[-1]:      # dosya uzantılı uçlar
                return None
            from django.shortcuts import render
            yanit = render(request, 'kabuk.html', {
                'kabuk_url': request.get_full_path(),
                'radyo': getattr(settings, 'GEEK_RADYO', {}),
            })
            yanit['Cache-Control'] = 'no-store'
            from django.utils.cache import patch_vary_headers
            patch_vary_headers(yanit, ('Sec-Fetch-Dest',))
            return yanit
        except Exception:
            return None
