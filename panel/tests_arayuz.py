"""Arayüz iyileştirmeleri: alt çubuk kısayolları, genel arama, şef yapılacaklar, şube karnesi."""
import datetime
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (Denetim, GeriBildirim, GeriBildirimDurum, GeriBildirimKategori, Rol, StokSayim, StokUrun,
                      Sube, TuketimAyar, TuketimFiyat, Urun)
from .tests_mola_stok import _AYAR, kisi


@override_settings(**_AYAR)
class ArayuzTesti(TestCase):
    def setUp(self):
        TuketimAyar.objects.all().delete()
        TuketimAyar.objects.create(aktif=True, baslangic=None)
        self.a = Sube.objects.create(ad='Alfa Şube')
        self.b = Sube.objects.create(ad='Beta Şube')
        self.urun = Urun.objects.create(form='HAMMADDE', kategori='ŞURUP', ad='VANILYA 750ML', koli_icerigi=12)
        StokUrun.objects.create(kategori='ŞURUP VE SOS', ad='VANILYA ŞURUP', kapali_icerik=750, sevkiyat_urun=self.urun)

    def sayfa(self, rol, sube=None, url='ana_sayfa'):
        p = kisi(rol, sube)
        self.client.force_login(p.user)
        return p, self.client.get(reverse(url), follow=True)

    def test_alt_cubuk_role_gore_kisayollar(self):
        beklenen = {Rol.SEF: ('Stok', 'Sevkiyat'), Rol.PERSONEL: ('Mola', 'Crew'), Rol.GENEL_MUDUR: ('Tüketim', 'Denetim'),
                    Rol.MUDUR: ('Denetim', 'Sevkiyat'), Rol.SATIN_ALMA: ('Stok', 'Tüketim')}
        for rol, (k1, k2) in beklenen.items():
            _, r = self.sayfa(rol, self.a if rol in (Rol.SEF, Rol.PERSONEL) else None)
            html = r.content.decode()
            bar = html[html.index('class="mobil-bar"'):]
            self.assertIn('<span>%s</span>' % k1, bar, rol)
            self.assertIn('<span>%s</span>' % k2, bar, rol)
            self.assertIn('<span>Menü</span>', bar)

    def test_arama_yetkiye_gore(self):
        TuketimFiyat.objects.create(urun=self.urun, grup='MERKEZ', fiyat=Decimal('10'), gecerli=datetime.date(2026, 1, 1))
        d = Denetim.objects.create(sube=self.a, tamamlandi=True, toplam_puan=64, bitis=timezone.now())
        gm = kisi(Rol.GENEL_MUDUR); self.client.force_login(gm.user)
        j = self.client.get(reverse('genel_ara'), {'q': 'alfa'}).json()['sonuc']
        self.assertEqual({x['tur'] for x in j}, {'Şube', 'Denetim'})
        j = self.client.get(reverse('genel_ara'), {'q': 'vanilya'}).json()['sonuc']
        self.assertEqual([x['tur'] for x in j], ['Ürün'])
        self.assertEqual(self.client.get(reverse('genel_ara'), {'q': 'a'}).json()['sonuc'], [])
        # şef: yalnız kendi şubesi, ürün fiyatı ve denetim yok
        sef = kisi(Rol.SEF, self.a); self.client.force_login(sef.user)
        j = self.client.get(reverse('genel_ara'), {'q': 'şube'}).json()['sonuc']
        self.assertEqual([x['etiket'] for x in j], ['Alfa Şube · tüketim raporu'])
        self.assertEqual(self.client.get(reverse('genel_ara'), {'q': 'vanilya'}).json()['sonuc'], [])
        # giriş yapmamış
        self.client.logout()
        self.assertEqual(self.client.get(reverse('genel_ara'), {'q': 'alfa'}).status_code, 403)

    def test_sef_yapilacaklar_ay_sonu(self):
        import calendar
        from unittest import mock
        from . import views
        sef = kisi(Rol.SEF, self.a)
        son = calendar.monthrange(2026, 10)[1]
        with mock.patch.object(views.timezone, 'localdate', return_value=datetime.date(2026, 10, son)):
            liste = views._sef_yapilacaklar(self.a)
        self.assertEqual(len(liste), 1); self.assertTrue(liste[0]['acil'])
        with mock.patch.object(views.timezone, 'localdate', return_value=datetime.date(2026, 10, 10)):
            self.assertEqual(views._sef_yapilacaklar(self.a), [])
        StokSayim.objects.create(sube=self.a, ay=datetime.date(2026, 10, 1))
        with mock.patch.object(views.timezone, 'localdate', return_value=datetime.date(2026, 10, son)):
            self.assertEqual(views._sef_yapilacaklar(self.a), [])
        # ayın ilk günlerinde geçen ay eksikse uyarır
        with mock.patch.object(views.timezone, 'localdate', return_value=datetime.date(2026, 11, 2)):
            self.assertEqual(views._sef_yapilacaklar(self.a), [])           # Ekim sayımı var
        with mock.patch.object(views.timezone, 'localdate', return_value=datetime.date(2026, 12, 2)):
            self.assertEqual(len(views._sef_yapilacaklar(self.a)), 1)       # Kasım sayımı eksik

    def test_sube_karnesi(self):
        Denetim.objects.create(sube=self.a, tamamlandi=True, toplam_puan=42, bitis=timezone.now())
        GeriBildirim.objects.create(sube=self.a, metin='x')
        gm = kisi(Rol.GENEL_MUDUR); self.client.force_login(gm.user)
        r = self.client.get(reverse('gosterge'))
        self.assertEqual(r.status_code, 200)
        k = r.context['karne']
        self.assertEqual([x['sube'].ad for x in k['satirlar']][0], 'Alfa Şube')    # en düşük puan üstte
        self.assertEqual(k['satirlar'][0]['gb'], 1)
        self.assertContains(r, 'Şube karnesi')
        # yetkisiz bölge müdürü denetim/geri bildirim sütununu görmez
        bm = kisi(Rol.MUDUR); bm.sorumlu_subeler.add(self.a); self.client.force_login(bm.user)
        k = self.client.get(reverse('gosterge')).context['karne']
        self.assertFalse(k['denetim']); self.assertFalse(k['gb'])
        self.assertEqual([x['sube'].ad for x in k['satirlar']], ['Alfa Şube'])


@override_settings(**_AYAR)
class GeriBildirimYonetimTesti(TestCase):
    def setUp(self):
        self.a = Sube.objects.create(ad='Alfa Şube')
        self.eski = GeriBildirim.objects.create(sube=self.a, metin='Eski şikayet', kategori=GeriBildirimKategori.SIKAYET)
        self.eski.olusturma = timezone.now() - datetime.timedelta(days=40); self.eski.save(update_fields=['olusturma'])
        self.yeni = GeriBildirim.objects.create(sube=self.a, metin='Yeni öneri', kategori=GeriBildirimKategori.ONERI)

    def test_yetkisiz_goremez(self):
        p = kisi(Rol.PERSONEL, self.a); self.client.force_login(p.user)
        self.assertEqual(self.client.get(reverse('geri_bildirim_yonetim')).status_code, 302)

    def test_varsayilan_tum_zamanlar_en_yeni_once(self):
        gm = kisi(Rol.GENEL_MUDUR); self.client.force_login(gm.user)
        r = self.client.get(reverse('geri_bildirim_yonetim'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual([b.metin for b in r.context['bildirimler']], ['Yeni öneri', 'Eski şikayet'])
        self.assertEqual(r.context['donem'], 'tum')

    def test_tarih_araligi_filtreler(self):
        gm = kisi(Rol.GENEL_MUDUR); self.client.force_login(gm.user)
        r = self.client.get(reverse('geri_bildirim_yonetim'), {'donem': 'ay'})
        self.assertEqual([b.metin for b in r.context['bildirimler']], ['Yeni öneri'])

    def test_eskiden_yeniye_siralama(self):
        gm = kisi(Rol.GENEL_MUDUR); self.client.force_login(gm.user)
        r = self.client.get(reverse('geri_bildirim_yonetim'), {'sirala': 'eski'})
        self.assertEqual([b.metin for b in r.context['bildirimler']], ['Eski şikayet', 'Yeni öneri'])

    def test_kategori_filtresi(self):
        gm = kisi(Rol.GENEL_MUDUR); self.client.force_login(gm.user)
        r = self.client.get(reverse('geri_bildirim_yonetim'), {'kategori': GeriBildirimKategori.SIKAYET})
        self.assertEqual([b.metin for b in r.context['bildirimler']], ['Eski şikayet'])

    def test_excel_ve_pdf_indir(self):
        gm = kisi(Rol.GENEL_MUDUR); self.client.force_login(gm.user)
        r = self.client.get(reverse('geri_bildirim_indir'), {'bicim': 'xlsx'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        r = self.client.get(reverse('geri_bildirim_indir'), {'bicim': 'pdf'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')

    def test_indir_yetkisiz(self):
        p = kisi(Rol.PERSONEL, self.a); self.client.force_login(p.user)
        self.assertEqual(self.client.get(reverse('geri_bildirim_indir')).status_code, 302)
