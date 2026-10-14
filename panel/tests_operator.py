"""Operatör süper admin + Geek Crew görünümü:  python manage.py test panel.tests_operator"""
import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Bildirim, GSosyalGonderi, GSosyalGorsel, Personel, Rol

_TMP = tempfile.mkdtemp(prefix='operator_test_')
_AYAR = dict(
    SECURE_SSL_REDIRECT=False, MEDIA_ROOT=_TMP,
    STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
              'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}},
)


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


def _png(ad='a.png', boy=(60, 90)):
    b = io.BytesIO()
    Image.new('RGB', boy, (200, 30, 30)).save(b, 'PNG')
    return SimpleUploadedFile(ad, b.getvalue(), content_type='image/png')


@override_settings(**_AYAR)
class OperatorYetkiTestleri(TestCase):
    def kisi(self, rol, ad=None, **kw):
        u = User.objects.create(username='u%d' % (User.objects.count() + 1))
        return Personel.objects.create(user=u, ad_soyad=ad or rol, rol=rol, **kw)

    def gir(self, p):
        self.client.force_login(p.user)

    def test_operator_gm_ile_ayni_sayfalara_girer(self):
        for ad in ('yedekler', 'soru_yonetimi'):
            for rol in (Rol.GENEL_MUDUR, Rol.OPERATOR):
                self.gir(self.kisi(rol))
                self.assertEqual(self.client.get(reverse(ad)).status_code, 200, (ad, rol))
            for rol in (Rol.MUDUR, Rol.YATIRIMCI, Rol.SEF, Rol.MAGAZA_MUDURU, Rol.PERSONEL, Rol.SATIN_ALMA):
                self.gir(self.kisi(rol))
                self.assertEqual(self.client.get(reverse(ad)).status_code, 302, (ad, rol))

    def test_menude_gorunur(self):
        self.gir(self.kisi(Rol.OPERATOR))
        sayfa = self.client.get(reverse('gosterge'))
        self.assertContains(sayfa, 'href="%s"' % reverse('yedekler'))
        self.assertContains(sayfa, 'href="%s"' % reverse('soru_yonetimi'))
        self.gir(self.kisi(Rol.MUDUR))
        sayfa = self.client.get(reverse('gosterge'))
        self.assertNotContains(sayfa, 'href="%s"' % reverse('yedekler'))

    def test_yedek_indirme_yetkisi(self):
        self.gir(self.kisi(Rol.MUDUR))
        self.assertEqual(self.client.get('/yedekler/gecersiz.sql').status_code, 404)

    def test_operator_geek_crew_marka_adiyla_paylasir(self):
        op = self.kisi(Rol.OPERATOR, 'Emir Gögebakan')
        diger = self.kisi(Rol.PERSONEL, 'Ali')
        self.gir(op)
        self.client.post(reverse('g_sosyal'), {'islem': 'gonderi_ekle', 'metin': 'Yeni menü!',
                                               'gorseller': [_png('1.png'), _png('2.png')]})
        g = GSosyalGonderi.objects.get()
        self.assertEqual(g.yazan_ad, 'Geek Coffee & Eatery')
        self.assertEqual(g.gorseller.count(), 2)
        self.assertEqual(Bildirim.objects.get(alici=diger).mesaj, 'Geek Coffee & Eatery yeni bir Geek Crew paylaşımı yaptı')
        sayfa = self.client.get(reverse('g_sosyal'))
        self.assertContains(sayfa, 'Geek Coffee &amp; Eatery')
        self.assertContains(sayfa, 'Resmî')
        self.assertNotContains(sayfa, 'gs-kim"><b>Emir')
        # personel görünümünde de marka adı + logo
        self.gir(diger)
        sayfa = self.client.get(reverse('g_sosyal'))
        self.assertContains(sayfa, 'icons/icon-192.png')
        self.assertContains(sayfa, 'Resmî')

    def test_gm_kendi_adiyla_paylasir(self):
        gm = self.kisi(Rol.GENEL_MUDUR, 'Mehmet Bey')
        self.gir(gm)
        self.client.post(reverse('g_sosyal'), {'islem': 'gonderi_ekle', 'metin': 'Selam'})
        self.assertEqual(GSosyalGonderi.objects.get().yazan_ad, 'Mehmet Bey')
        self.assertNotContains(self.client.get(reverse('g_sosyal')), 'Resmî')

    def test_tam_cerceve_medya_ve_galeri(self):
        gm = self.kisi(Rol.GENEL_MUDUR)
        g = GSosyalGonderi.objects.create(yazan=gm, yazan_ad='X', metin='m')
        for i in range(3):
            GSosyalGorsel.objects.create(gonderi=g, gorsel=_png('%d.png' % i), sira=i)
        tek = GSosyalGonderi.objects.create(yazan=gm, yazan_ad='X', metin='t')
        GSosyalGorsel.objects.create(gonderi=tek, gorsel=_png('t.png'))
        self.gir(gm)
        s = self.client.get(reverse('g_sosyal')).content.decode()
        self.assertEqual(s.count('class="gs-slayt-oge lb-tetikleyici"'), 4)
        self.assertIn('data-grup="g%d"' % g.id, s)
        self.assertIn('1/3', s)
        self.assertEqual(s.count('gs-medya coklu'), 1)          # yalnız çoklu gönderide ok/sayaç
        self.assertNotIn('gs-izgara', s)                         # kırpan eski ızgara kalmadı
