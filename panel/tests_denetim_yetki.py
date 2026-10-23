"""Denetim görüntüleme yetkisi, çoklu fotoğraf, PDF, GM yetkileri, koşu skor sınırı."""
import base64
import io

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (Denetim, DenetimBolum, DenetimCevap, DenetimFoto, DenetimMadde, OyunSkor, Rol, Sube)
from .tests_mola_stok import _AYAR, kisi


def _jpeg(renk=(200, 30, 30), boyut=(300, 200)):
    from PIL import Image
    b = io.BytesIO()
    Image.new('RGB', boyut, renk).save(b, 'JPEG')
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()


@override_settings(**_AYAR)
class DenetimYetkiTesti(TestCase):
    def setUp(self):
        self.a = Sube.objects.create(ad='Alfa')
        self.b = Sube.objects.create(ad='Beta')
        bolum = DenetimBolum.objects.create(ad='A. Genel', sira=1)
        self.m1 = DenetimMadde.objects.create(bolum=bolum, metin='Cam temiz mi?', sira=1)
        self.m2 = DenetimMadde.objects.create(bolum=bolum, metin='Zemin temiz mi?', sira=2)
        self.gm = kisi(Rol.GENEL_MUDUR)
        self.bm = kisi(Rol.MUDUR)
        self.bm.sorumlu_subeler.add(self.a)
        self.da = self.bitmis(self.a)
        self.db = self.bitmis(self.b)

    def bitmis(self, sube):
        d = Denetim.objects.create(sube=sube, denetleyen=self.gm, tamamlandi=True, toplam_puan=70)
        DenetimCevap.objects.create(denetim=d, madde=self.m1, puan=2, not_metni='kirli')
        DenetimCevap.objects.create(denetim=d, madde=self.m2, puan=5)
        return d

    def test_bolge_muduru_yetkisiz_goremez(self):
        self.client.force_login(self.bm.user)
        self.assertEqual(self.client.get(reverse('denetim_sonuclar')).status_code, 302)
        self.assertEqual(self.client.get(reverse('denetim_detay', args=[self.da.id])).status_code, 302)

    def test_yetkili_bolge_muduru_yalniz_sorumlu_subeler(self):
        self.bm.denetim_goruntuleyici = True; self.bm.save()
        self.client.force_login(self.bm.user)
        r = self.client.get(reverse('denetim_sonuclar'))
        self.assertContains(r, 'Alfa'); self.assertNotContains(r, 'Beta')
        self.assertEqual(self.client.get(reverse('denetim_detay', args=[self.da.id])).status_code, 200)
        self.assertEqual(self.client.get(reverse('denetim_detay', args=[self.db.id])).status_code, 302)
        self.assertEqual(self.client.get(reverse('denetim_pdf_indir', args=[self.db.id])).status_code, 302)
        self.assertTrue(self.client.get(reverse('denetim_pdf_indir', args=[self.da.id])).content.startswith(b'%PDF'))

    def test_ekipten_yetki_verme(self):
        self.client.force_login(self.gm.user)
        self.client.post(reverse('ekip'), {'islem': 'dn_yetki_ekle', 'personel_id': self.bm.id})
        self.bm.refresh_from_db(); self.assertTrue(self.bm.denetim_goruntuleyici)
        self.client.post(reverse('ekip'), {'islem': 'dn_yetki_cikar', 'personel_id': self.bm.id})
        self.bm.refresh_from_db(); self.assertFalse(self.bm.denetim_goruntuleyici)
        self.assertContains(self.client.get(reverse('ekip')), 'Denetim Sonuçları Yetkisi')

    def test_bir_maddeye_cok_fotograf_ve_pdf(self):
        d = Denetim.objects.create(sube=self.a, denetleyen=self.bm)
        c1 = DenetimCevap.objects.create(denetim=d, madde=self.m1)
        DenetimCevap.objects.create(denetim=d, madde=self.m2)
        self.client.force_login(self.bm.user)
        veri = {'islem': 'kaydet', 'puan_%d' % c1.id: '1', 'foto_b64_%d' % c1.id: [_jpeg(), _jpeg((0, 90, 200)), _jpeg((0, 150, 0))]}
        r = self.client.post(reverse('denetim_doldur', args=[d.id]), veri)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(DenetimFoto.objects.filter(cevap=c1).count(), 3)
        # sınır: en fazla 6
        self.client.post(reverse('denetim_doldur', args=[d.id]), {'islem': 'kaydet', 'foto_b64_%d' % c1.id: [_jpeg()] * 9})
        self.assertEqual(DenetimFoto.objects.filter(cevap=c1).count(), 6)
        # silme
        f = DenetimFoto.objects.filter(cevap=c1).first()
        self.client.post(reverse('denetim_doldur', args=[d.id]), {'islem': 'kaydet', 'foto_sil_%d' % c1.id: [str(f.id)]})
        self.assertEqual(DenetimFoto.objects.filter(cevap=c1).count(), 5)
        self.client.post(reverse('denetim_doldur', args=[d.id]), {'islem': 'bitir'})
        pdf = self.client.get(reverse('denetim_pdf_indir', args=[d.id]))
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertContains(self.client.get(reverse('denetim_detay', args=[d.id])), 'lb-tetikleyici')
        self.assertContains(self.client.get(reverse('denetim_doldur', args=[d.id]), follow=True), 'Cam temiz')

    def test_gm_operator_yetkileri(self):
        from . import views
        for lst in (views.EGITIM_DUZENLE_ROLLER, views.EGITIM_AYAR_ROLLER, views.EGITIM_ACIK_PUANLA_ROLLER):
            self.assertIn(Rol.GENEL_MUDUR, lst)
        self.client.force_login(self.gm.user)
        self.assertContains(self.client.get(reverse('g_sosyal')), 'anket')

    def test_kosu_200bin_ustu_kabul(self):
        p = kisi(Rol.PERSONEL, self.a)
        self.client.force_login(p.user)
        r = self.client.post(reverse('geek_kosu_skor'), {'skor': 250000, 'sure_sn': 1800, 'mod': 'kosu'})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(OyunSkor.objects.filter(personel=p).first().skor, 250000)
        # süreye göre imkânsız skor yine reddedilir
        p2 = kisi(Rol.PERSONEL, self.a); self.client.force_login(p2.user)
        r = self.client.post(reverse('geek_kosu_skor'), {'skor': 250000, 'sure_sn': 60, 'mod': 'kosu'})
        self.assertEqual(r.status_code, 400)


@override_settings(**_AYAR)
class DenetimPuanTesti(TestCase):
    def test_bos_maddeler_sifir_sayilir(self):
        gm = kisi(Rol.GENEL_MUDUR); s = Sube.objects.create(ad='P')
        bolum = DenetimBolum.objects.create(ad='A', sira=1)
        maddeler = [DenetimMadde.objects.create(bolum=bolum, metin='m%d' % i, sira=i) for i in range(10)]
        d = Denetim.objects.create(sube=s, denetleyen=gm)
        cev = [DenetimCevap.objects.create(denetim=d, madde=m) for m in maddeler]
        self.client.force_login(gm.user)
        veri = {'islem': 'bitir'}
        for c in cev[:2]:
            veri['puan_%d' % c.id] = '5'          # 10 maddeden 2'si tam puan
        self.client.post(reverse('denetim_doldur', args=[d.id]), veri)
        d.refresh_from_db()
        self.assertEqual(d.toplam_puan, 20.0)     # eski kuralda 100 çıkardı
