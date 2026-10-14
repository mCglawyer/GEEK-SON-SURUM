"""Mola (QR okutunca başlar, 15/45 sonradan) ve stok ay seçimi:  python manage.py test panel.tests_mola_stok"""
import datetime

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (MolaOturum, MolaQRAyar, Personel, Rol, StokSayim, StokUrun, Sube, SubeMolaToken)

_AYAR = dict(
    SECURE_SSL_REDIRECT=False,
    STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
              'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}},
)


def kisi(rol, sube=None, ad=None):
    u = User.objects.create(username='u%d' % (User.objects.count() + 1))
    return Personel.objects.create(user=u, ad_soyad=ad or rol, rol=rol, sube=sube)


@override_settings(**_AYAR)
class MolaTestleri(TestCase):
    def setUp(self):
        self.sube = Sube.objects.create(ad='Merkez')
        MolaQRAyar.objects.create(acik=True)
        self.tok = SubeMolaToken.objects.create(sube=self.sube, token='tok123')
        self.p = kisi(Rol.PERSONEL, self.sube)
        self.client.force_login(self.p.user)
        self.url = reverse('mola_qr_giris', args=['tok123'])

    def test_qr_okutunca_mola_hemen_baslar(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        m = MolaOturum.objects.get(personel=self.p)
        self.assertFalse(m.sure_secildi)
        self.assertEqual(m.sure_dk, 45)
        self.assertIsNone(m.bitis)
        self.assertContains(r, 'Ne kadar mola kullanacaksın')

    def test_yenileme_ikinci_mola_acmaz(self):
        self.client.get(self.url); self.client.get(self.url)
        self.assertEqual(MolaOturum.objects.filter(personel=self.p).count(), 1)

    def test_sure_sonradan_secilir_baslangic_degismez(self):
        self.client.get(self.url)
        m = MolaOturum.objects.get(personel=self.p)
        MolaOturum.objects.filter(pk=m.pk).update(baslangic=timezone.now() - datetime.timedelta(minutes=5))
        bas = MolaOturum.objects.get(pk=m.pk).baslangic
        self.client.post(self.url, {'islem': 'sure_sec', 'sure': '15'})
        m.refresh_from_db()
        self.assertEqual(m.sure_dk, 15)
        self.assertTrue(m.sure_secildi)
        self.assertEqual(m.baslangic, bas)

    def test_sure_bir_kez_secilir_ve_gecersiz_deger_reddedilir(self):
        self.client.get(self.url)
        self.client.post(self.url, {'islem': 'sure_sec', 'sure': '99'})
        m = MolaOturum.objects.get(personel=self.p)
        self.assertFalse(m.sure_secildi)
        self.client.post(self.url, {'islem': 'sure_sec', 'sure': '15'})
        self.client.post(self.url, {'islem': 'sure_sec', 'sure': '45'})
        m.refresh_from_db()
        self.assertEqual(m.sure_dk, 15)

    def test_bitir(self):
        self.client.get(self.url)
        self.client.post(self.url, {'islem': 'bitir'})
        m = MolaOturum.objects.get(personel=self.p)
        self.assertIsNotNone(m.bitis)

    def test_bitir_sonrasi_yeni_mola_baslamaz(self):
        self.client.get(self.url)
        r = self.client.post(self.url, {'islem': 'bitir'}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(MolaOturum.objects.filter(personel=self.p).count(), 1)
        self.assertFalse(MolaOturum.objects.filter(personel=self.p, bitis__isnull=True).exists())
        self.assertContains(r, 'Molan bitti')
        # sayfa yenilense de yeni mola açılmaz
        self.client.get(r.redirect_chain[-1][0])
        self.assertFalse(MolaOturum.objects.filter(personel=self.p, bitis__isnull=True).exists())

    def test_bitirdikten_sonra_qr_tekrar_okutulursa_yeni_mola_baslar(self):
        self.client.get(self.url)
        self.client.post(self.url, {'islem': 'bitir'})
        self.client.get(self.url)
        self.assertEqual(MolaOturum.objects.filter(personel=self.p).count(), 2)

    def test_eski_sekmeden_ikinci_bitir_yeni_mola_acmaz(self):
        self.client.get(self.url)
        self.client.post(self.url, {'islem': 'bitir'})
        self.client.post(self.url, {'islem': 'bitir'}, follow=True)
        self.assertEqual(MolaOturum.objects.filter(personel=self.p).count(), 1)

    def test_qr_kapaliyken_mola_acilmaz(self):
        MolaQRAyar.objects.update(acik=False)
        self.client.get(self.url)
        self.assertEqual(MolaOturum.objects.count(), 0)

    def test_gecersiz_token_mola_acmaz(self):
        self.client.get(reverse('mola_qr_giris', args=['yok']))
        self.assertEqual(MolaOturum.objects.count(), 0)


@override_settings(**_AYAR)
class StokAyTestleri(TestCase):
    def setUp(self):
        self.sube = Sube.objects.create(ad='Merkez')
        self.sef = kisi(Rol.SEF, self.sube)
        self.urun = StokUrun.objects.create(ad='Süt', kapali_icerik=12)
        self.client.force_login(self.sef.user)
        bu = timezone.localdate().replace(day=1)
        self.bu = bu
        self.onceki = (bu - datetime.timedelta(days=1)).replace(day=1)

    def kaydet(self, kayit_ay=None):
        d = {'islem': 'stok_kaydet', 'kapali_%d' % self.urun.id: '3'}
        if kayit_ay:
            d['kayit_ay'] = kayit_ay
        return self.client.post(reverse('stok'), d)

    def test_onay_penceresi_iki_ayi_sunar(self):
        r = self.client.get(reverse('stok'))
        self.assertContains(r, 'Bu hangi ayın stoğu?')
        self.assertContains(r, 'data-ay="%s"' % self.bu.strftime('%Y-%m'))
        self.assertContains(r, 'data-ay="%s"' % self.onceki.strftime('%Y-%m'))

    def test_onceki_ay_secilirse_oraya_yazilir(self):
        self.kaydet(self.onceki.strftime('%Y-%m'))
        self.assertTrue(StokSayim.objects.filter(sube=self.sube, ay=self.onceki).exists())
        self.assertFalse(StokSayim.objects.filter(sube=self.sube, ay=self.bu).exists())

    def test_bu_ay_secilirse_bu_aya_yazilir(self):
        self.kaydet(self.bu.strftime('%Y-%m'))
        self.assertTrue(StokSayim.objects.filter(sube=self.sube, ay=self.bu).exists())

    def test_izinsiz_ay_secimi_yok_sayilir(self):
        self.kaydet('2019-01')
        self.assertFalse(StokSayim.objects.filter(ay=datetime.date(2019, 1, 1)).exists())
        self.assertTrue(StokSayim.objects.filter(sube=self.sube, ay=self.bu).exists())

    def test_secim_yoksa_ekrandaki_aya_yazar(self):
        self.kaydet()
        self.assertTrue(StokSayim.objects.filter(sube=self.sube, ay=self.bu).exists())

    def test_var_olan_kayit_isaretlenir(self):
        StokSayim.objects.create(sube=self.sube, ay=self.onceki)
        r = self.client.get(reverse('stok'))
        self.assertContains(r, 'kayıt var, güncellenir')
