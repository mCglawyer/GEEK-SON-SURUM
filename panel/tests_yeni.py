"""Kalibrasyon tiki, müdür girişleri, mesai QR hatırlatması, lavabo satırları, eğitmen adayı."""
import datetime

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (Anket, AnketOy, Bildirim, Kalibrasyon, KalibrasyonKontrol, LavaboDenetim, MesaiKayit, OnayDurumu, OturumKaydi,
                     Rol, Sube, Vardiya)
from .tests_mola_stok import _AYAR, kisi


@override_settings(**_AYAR)
class KalibrasyonTikTestleri(TestCase):
    def setUp(self):
        self.sube = Sube.objects.create(ad='Merkez')
        self.diger = Sube.objects.create(ad='Diğer')
        self.sef = kisi(Rol.SEF, self.sube, 'Şef Ayşe')
        self.sef2 = kisi(Rol.SEF, self.diger, 'Şef Diğer')
        self.pers = kisi(Rol.PERSONEL, self.sube, 'Personel')
        self.gm = kisi(Rol.GENEL_MUDUR, None, 'GM')
        self.mudur = kisi(Rol.MUDUR, None, 'Bölge Bora')
        self.mudur.sorumlu_subeler.add(self.sube)
        self.k = Kalibrasyon(sube=self.sube, giren=self.pers, giren_ad='Personel')
        self.k.foto.save('a.jpg', ContentFile(b'x' * 200), save=True)

    def tikla(self, kisi_, kid=None, sube=None):
        self.client.force_login(kisi_.user)
        url = reverse('kalibrasyon') + ('?sube_id=%d' % sube.id if sube else '')
        return self.client.post(url, {'islem': 'kalibrasyon_kontrol', 'kid': kid or self.k.id})

    def test_sef_tik_atar_ve_geri_alir(self):
        self.tikla(self.sef)
        self.assertEqual(KalibrasyonKontrol.objects.filter(kalibrasyon=self.k, personel=self.sef).count(), 1)
        self.tikla(self.sef)
        self.assertEqual(KalibrasyonKontrol.objects.count(), 0)

    def test_mudur_tik_atar(self):
        self.tikla(self.mudur, sube=self.sube)
        self.assertEqual(KalibrasyonKontrol.objects.filter(personel=self.mudur).count(), 1)

    def test_baska_subenin_sefi_atamaz(self):
        self.tikla(self.sef2)
        self.assertEqual(KalibrasyonKontrol.objects.count(), 0)

    def test_personel_ve_gm_atamaz(self):
        self.tikla(self.pers)
        self.tikla(self.gm, sube=self.sube)
        self.assertEqual(KalibrasyonKontrol.objects.count(), 0)

    def test_sayfa_durumu_gosterir(self):
        self.client.force_login(self.sef.user)
        r = self.client.get(reverse('kalibrasyon'))
        self.assertContains(r, 'Kontrol bekliyor')
        self.assertContains(r, 'Kontrol ettim')
        self.tikla(self.sef)
        r = self.client.get(reverse('kalibrasyon'))
        self.assertContains(r, 'Şef Ayşe')
        self.assertContains(r, 'Tiki kaldır')
        self.client.force_login(self.gm.user)
        r = self.client.get(reverse('kalibrasyon') + '?sube_id=%d' % self.sube.id)
        self.assertContains(r, 'Şef Ayşe')
        self.assertNotContains(r, 'Kontrol ettim')


@override_settings(**_AYAR)
class MudurGirisTestleri(TestCase):
    def setUp(self):
        self.sube = Sube.objects.create(ad='Merkez')
        self.mudur = kisi(Rol.MUDUR, None, 'Bölge Bora')
        self.gm = kisi(Rol.GENEL_MUDUR, None, 'GM')
        self.op = kisi(Rol.OPERATOR, None, 'Op')
        self.yat = kisi(Rol.YATIRIMCI, None, 'Yatırımcı')
        self.sef = kisi(Rol.SEF, self.sube, 'Şef')

    def test_giris_kaydedilir_yalniz_mudur(self):
        self.client.force_login(self.mudur.user)
        self.assertEqual(OturumKaydi.objects.filter(personel=self.mudur, tur='giris').count(), 1)
        self.client.force_login(self.sef.user)
        self.assertEqual(OturumKaydi.objects.exclude(personel=self.mudur).count(), 0)

    def test_acilis_30dk_sonra_sayilir(self):
        self.client.force_login(self.mudur.user)
        self.client.get(reverse('kalibrasyon'))
        self.client.get(reverse('kalibrasyon'))
        self.assertEqual(OturumKaydi.objects.filter(tur='acilis').count(), 0)
        s = self.client.session
        s['_izle_son'] = s['_izle_son'] - 3600
        s.save()
        self.client.get(reverse('kalibrasyon'))
        self.assertEqual(OturumKaydi.objects.filter(tur='acilis').count(), 1)

    def test_sayfa_yetkisi(self):
        for k in (self.gm, self.op, self.yat):
            self.client.force_login(k.user)
            self.assertEqual(self.client.get(reverse('mudur_girisleri')).status_code, 200, k.rol)
        for k in (self.mudur, self.sef):
            self.client.force_login(k.user)
            self.assertEqual(self.client.get(reverse('mudur_girisleri')).status_code, 302, k.rol)

    def test_sayfa_sayiyi_gosterir(self):
        OturumKaydi.objects.create(personel=self.mudur, tur='giris')
        OturumKaydi.objects.create(personel=self.mudur, tur='acilis')
        self.client.force_login(self.gm.user)
        r = self.client.get(reverse('mudur_girisleri'))
        self.assertContains(r, 'Bölge Bora')
        self.assertEqual(r.context['toplam_giris'], 2)
        self.assertEqual(r.context['satirlar'][0]['adet'], 2)


@override_settings(**_AYAR)
class MesaiHatirlatTestleri(TestCase):
    def setUp(self):
        self.sube = Sube.objects.create(ad='Merkez')
        self.sef = kisi(Rol.SEF, self.sube, 'Şef')
        self.p1 = kisi(Rol.PERSONEL, self.sube, 'Sabahçı Ali')
        self.p2 = kisi(Rol.PERSONEL, self.sube, 'Akşamcı Veli')
        self.p3 = kisi(Rol.PERSONEL, self.sube, 'İzinli')
        self.gun = datetime.date(2026, 10, 15)
        for p, tip in ((self.p1, 'Sabahçı'), (self.p2, 'Akşamcı'), (self.p3, 'İzinli'), (self.sef, 'Sabahçı')):
            Vardiya.objects.create(personel=p, tarih=self.gun, vardiya_tipi=tip, durum=OnayDurumu.ONAYLANDI)
        self.gonderilen = []

    def an(self, h, m):
        return timezone.make_aware(datetime.datetime(2026, 10, 15, h, m))

    def calistir(self, h, m):
        from .mesai_hatirlat import calistir
        return calistir(self.an(h, m), bildir=lambda al, msg, link, tur: [
            Bildirim.objects.create(alici=a, mesaj=msg, link=link, tur=tur) for a in al])

    def test_15_dk_once_sabahcilara(self):
        self.assertEqual(self.calistir(7, 15), 2)         # p1 + şef
        self.assertEqual(set(Bildirim.objects.values_list('alici_id', flat=True)), {self.p1.id, self.sef.id})
        self.assertIn('07.30–16.30', Bildirim.objects.first().mesaj)

    def test_erken_ve_cok_gec_gonderilmez(self):
        self.assertEqual(self.calistir(7, 0), 0)
        self.assertEqual(self.calistir(8, 45), 0)

    def test_ikinci_kez_ayni_bildirim_gitmez(self):
        self.calistir(7, 15)
        self.assertEqual(self.calistir(7, 20), 0)

    def test_okutan_tekrar_almaz_okutmayan_alir(self):
        self.calistir(7, 15)
        MesaiKayit.objects.create(sube=self.sube, personel=self.p1, giris=self.an(7, 28))
        self.assertEqual(self.calistir(7, 46), 1)          # yalnız şef
        son = Bildirim.objects.filter(tur='mesai_qr2').get()
        self.assertEqual(son.alici_id, self.sef.id)
        self.assertEqual(self.calistir(7, 50), 0)

    def test_aksamcilar(self):
        self.assertEqual(self.calistir(15, 20), 1)
        self.assertIn('15.30–00.30', Bildirim.objects.get().mesaj)


    def test_bitiste_cikis_hatirlatmasi(self):
        MesaiKayit.objects.create(sube=self.sube, personel=self.p1, giris=self.an(7, 28))
        MesaiKayit.objects.create(sube=self.sube, personel=self.sef, giris=self.an(7, 29), cikis=self.an(16, 29))
        self.assertEqual(self.calistir(16, 31), 1)          # yalnız çıkışı açık kalan p1
        b = Bildirim.objects.get()
        self.assertEqual((b.alici_id, b.tur), (self.p1.id, 'mesai_cikis'))
        Bildirim.objects.update(olusturma=self.an(16, 31))   # test saati gerçek saatten farklı
        self.assertEqual(self.calistir(16, 35), 0)
        self.assertEqual(self.calistir(16, 50), 1)          # tekrar
        self.assertTrue(Bildirim.objects.filter(tur='mesai_cikis2').exists())

    def test_aksamci_gece_yarisi_sonrasi_cikis(self):
        MesaiKayit.objects.create(sube=self.sube, personel=self.p2, giris=self.an(15, 28))
        sonra = timezone.make_aware(datetime.datetime(2026, 10, 16, 0, 31))
        from .mesai_hatirlat import calistir
        n = calistir(sonra, bildir=lambda al, msg, link, tur: [
            Bildirim.objects.create(alici=a, mesaj=msg, link=link, tur=tur) for a in al])
        self.assertEqual(n, 1)
        self.assertEqual(Bildirim.objects.get().alici_id, self.p2.id)


@override_settings(**_AYAR)
class LavaboSatirTestleri(TestCase):
    def setUp(self):
        self.sube = Sube.objects.create(ad='Merkez')
        self.sef = kisi(Rol.SEF, self.sube, 'Şef')
        self.gm = kisi(Rol.GENEL_MUDUR, None, 'GM')

    def test_saat_saat_satirlar(self):
        for i in range(2):
            d = LavaboDenetim(sube=self.sube, giren=self.sef, giren_ad='Şef')
            d.foto.save('l%d.jpg' % i, ContentFile(b'x' * 200), save=True)
        self.client.force_login(self.gm.user)
        r = self.client.get(reverse('lavabo') + '?sube_id=%d' % self.sube.id)
        self.assertContains(r, 'lv-satir')
        j = self.client.get(reverse('lavabo_json') + '?sube_id=%d' % self.sube.id).json()
        self.assertIn('lv-saat', j['html'])


@override_settings(**_AYAR)
class EgitmenAdayTestleri(TestCase):
    def test_bolge_muduru_egitmen_olabilir(self):
        gm = kisi(Rol.GENEL_MUDUR, None, 'GM')
        m = kisi(Rol.MUDUR, None, 'Bölge Bora')
        self.client.force_login(gm.user)
        r = self.client.get(reverse('ekip'))
        self.assertIn(m, list(r.context['egitmen_adaylari']))
        self.client.post(reverse('ekip'), {'islem': 'egitmen_ekle', 'personel_id': m.id})
        m.refresh_from_db()
        self.assertTrue(m.egitmen)


@override_settings(**_AYAR)
class RadyoTestleri(TestCase):
    def test_geek_crew_radyoyu_gomer_playlisti_kaldirir(self):
        p = kisi(Rol.GENEL_MUDUR, None, 'GM')
        self.client.force_login(p.user)
        r = self.client.get(reverse('g_sosyal'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="radyo"')
        self.assertContains(r, 'radio.geekpanel.net/api/nowplaying/geekradio')
        self.assertContains(r, 'js/radyo.js')
        self.assertNotContains(r, 'Geek Playlist')
        self.assertNotContains(r, 'music.youtube.com')


@override_settings(**_AYAR)
class DegerlendirmeVeAnketTestleri(TestCase):
    def setUp(self):
        from .models import MusteriDegerlendirme, SubeDegerlendirmeToken
        self.sube = Sube.objects.create(ad='Merkez')
        self.tok = SubeDegerlendirmeToken.objects.create(sube=self.sube, token='tok-abc')
        self.url = reverse('musteri_degerlendirme', args=['tok-abc'])
        self.gm = kisi(Rol.GENEL_MUDUR, None, 'GM')
        self.op = kisi(Rol.OPERATOR, None, 'Op')
        self.yat = kisi(Rol.YATIRIMCI, None, 'Yat')
        self.pers = kisi(Rol.PERSONEL, self.sube, 'Personel')
        self.MD = MusteriDegerlendirme

    # --- müşteri formu ve Google yönlendirmesi
    def test_puan_secilmeden_gonderilmez(self):
        r = self.client.post(self.url, {'uc_kelime': 'güzel'})
        self.assertContains(r, 'bir puan seç')
        self.assertEqual(self.MD.objects.count(), 0)

    def test_8_ve_uzeri_google_baglantisi_varsa_yonlendirilir(self):
        self.sube.google_yorum_url = 'https://g.page/r/ABC/review'
        self.sube.save()
        for puan in (8, 9, 10):
            r = self.client.post(self.url, {'puan': str(puan)})
            self.assertContains(r, 'https://g.page/r/ABC/review')
            self.assertContains(r, 'Google')

    def test_8_alti_uygulamada_kalir(self):
        self.sube.google_yorum_url = 'https://g.page/r/ABC/review'
        self.sube.save()
        for puan in (0, 5, 7):
            r = self.client.post(self.url, {'puan': str(puan)})
            self.assertNotContains(r, 'g.page')
            self.assertContains(r, 'Teşekkür')
        self.assertEqual(self.MD.objects.count(), 3)          # yine de kaydedilir

    def test_yuksek_puan_ama_baglanti_yoksa_yonlenmez(self):
        r = self.client.post(self.url, {'puan': '10'})
        self.assertNotContains(r, 'Google')
        self.assertEqual(self.MD.objects.count(), 1)

    def test_google_baglantisi_kaydedilir_yalniz_https(self):
        self.client.force_login(self.gm.user)
        self.client.post(reverse('degerlendirme_qr_yonetim'), {
            'islem': 'google_kaydet', 'sube_id': self.sube.id, 'google_yorum_url': 'http://x.com'})
        self.sube.refresh_from_db(); self.assertEqual(self.sube.google_yorum_url, '')
        self.client.post(reverse('degerlendirme_qr_yonetim'), {
            'islem': 'google_kaydet', 'sube_id': self.sube.id, 'google_yorum_url': 'https://g.page/r/ABC/review'})
        self.sube.refresh_from_db(); self.assertEqual(self.sube.google_yorum_url, 'https://g.page/r/ABC/review')

    # --- değerlendirme silme
    def test_silme_yetkisi_ve_toplu_silme(self):
        a = self.MD.objects.create(sube=self.sube, puan=3)
        b = self.MD.objects.create(sube=self.sube, puan=9)
        c = self.MD.objects.create(sube=self.sube, puan=7)
        self.client.force_login(self.yat.user)                       # yatırımcı görür ama silemez
        self.client.post(reverse('degerlendirmeler'), {'islem': 'sil', 'id': a.id})
        self.assertEqual(self.MD.objects.count(), 3)
        self.client.force_login(self.gm.user)
        r = self.client.post(reverse('degerlendirmeler'), {'islem': 'sil', 'id': a.id}, follow=True)
        self.assertContains(r, '1 değerlendirme silindi')
        self.client.post(reverse('degerlendirmeler'), {'islem': 'sil_secili', 'secili': [b.id, c.id]})
        self.assertEqual(self.MD.objects.count(), 0)

    # --- anket
    def test_yalniz_operator_anket_paylasir(self):
        veri = {'islem': 'anket_ekle', 'soru': 'Yeni menü?', 'secenek': ['Evet', 'Hayır']}
        for k in (self.gm, self.pers, self.yat):
            self.client.force_login(k.user)
            self.client.post(reverse('g_sosyal'), veri)
        self.assertEqual(Anket.objects.count(), 0)
        self.client.force_login(self.op.user)
        self.client.post(reverse('g_sosyal'), veri)
        self.assertEqual(Anket.objects.count(), 1)
        self.assertEqual(Anket.objects.get().secenekler.count(), 2)
        self.assertTrue(Bildirim.objects.filter(alici=self.pers, mesaj__contains='anket').exists())

    def test_anket_en_az_iki_secenek(self):
        self.client.force_login(self.op.user)
        self.client.post(reverse('g_sosyal'), {'islem': 'anket_ekle', 'soru': 'x', 'secenek': ['Tek', '']})
        self.assertEqual(Anket.objects.count(), 0)

    def test_oy_bir_kez_sonuclari_herkes_gorur_kapaliyken_oy_yok(self):
        self.client.force_login(self.op.user)
        self.client.post(reverse('g_sosyal'), {'islem': 'anket_ekle', 'soru': 'Yeni menü?', 'secenek': ['Evet', 'Hayır']})
        a = Anket.objects.get()
        evet, hayir = list(a.secenekler.all())
        self.client.force_login(self.pers.user)
        self.client.post(reverse('g_sosyal'), {'islem': 'anket_oy', 'anket_id': a.id, 'secenek_id': evet.id})
        self.client.post(reverse('g_sosyal'), {'islem': 'anket_oy', 'anket_id': a.id, 'secenek_id': hayir.id})   # ikinci oy
        self.assertEqual(AnketOy.objects.count(), 1)
        self.client.force_login(self.gm.user)
        self.client.post(reverse('g_sosyal'), {'islem': 'anket_oy', 'anket_id': a.id, 'secenek_id': hayir.id})
        r = self.client.get(reverse('g_sosyal'))
        k = r.context['anketler'][0]
        self.assertEqual((k['toplam'], k['secenekler'][0]['yuzde'], k['secenekler'][1]['yuzde']), (2, 50, 50))
        self.assertContains(r, '%50')
        # başkası anketi kapatamaz, operatör kapatır; kapalı ankete oy verilemez
        self.client.post(reverse('g_sosyal'), {'islem': 'anket_kapat', 'anket_id': a.id})
        a.refresh_from_db(); self.assertTrue(a.aktif)
        self.client.force_login(self.op.user)
        self.client.post(reverse('g_sosyal'), {'islem': 'anket_kapat', 'anket_id': a.id})
        a.refresh_from_db(); self.assertFalse(a.aktif)
        self.client.post(reverse('g_sosyal'), {'islem': 'anket_oy', 'anket_id': a.id, 'secenek_id': evet.id})
        self.assertEqual(AnketOy.objects.count(), 2)

    def test_sayfa_gizli_ogeleri_gostermez(self):
        """[hidden] her zaman gizler (şube denetimi kamera penceresi hata kaydı)."""
        import os
        from django.conf import settings
        css = open(os.path.join(settings.BASE_DIR, 'static/css/tema.css'), encoding='utf-8').read()
        self.assertIn('[hidden]{display:none !important}', css)
