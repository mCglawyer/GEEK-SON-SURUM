"""QR Menü Yönetimi testleri:  python manage.py test panel.tests_menu"""
import csv
import io
import shutil
import tempfile
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .menu_sema import MARKALAR
from .menu_yayin import csv_satirlari, csv_uret
from .models import MenuKategori, MenuMarka, MenuUrun, Personel, Rol

_TMP = tempfile.mkdtemp(prefix='menu_test_')
_AYAR = dict(
    SECURE_SSL_REDIRECT=False, MEDIA_ROOT=_TMP,
    STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
              'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}},
)


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


def _csv_yaz(yol, sutunlar, satirlar):
    with open(yol, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(sutunlar)
        for s in satirlar:
            w.writerow([s.get(c, '') for c in sutunlar])


def _geek_satirlari():
    return [
        dict(kod='avokado-tost', kategori_kodu='tost', kategori='Tostlar', kategori_en='Toasts', urun_adi='Avokado Tost',
             urun_adi_en='Avocado Toast', fiyat='245,50', aciklama='Çıtır ekmek,\navokado', kalori='320', protein='12,5',
             gluten='TRUE', sut='TRUE', vegan='FALSE', gorsel_link='https://lh3.googleusercontent.com/d/AAA'),
        dict(kod='serpme', kategori_kodu='yumurta', kategori='Kahvaltılar', kategori_en='Breakfast', urun_adi='Serpme',
             fiyat='450', yumurta='TRUE', sert_kabuklu_yemis='TRUE', koruyucu_madde='TRUE', protein='45'),
        dict(kod='', kategori_kodu='wrapbowl', kategori='Wrap\'ler', urun_adi='Tavuk Wrap', fiyat='300', vegan='TRUE'),
        dict(kod='bos', kategori_kodu='tost', urun_adi='   ', fiyat='1'),          # boş ad -> atlanır
    ]


def _baga_satirlari():
    return [
        dict(kod='baga-burger', kategori_kodu='hamburgerler', kategori='Hamburgerler', kategori_en='Burgers',
             urun_adi='Baga Burger', fiyat='280', icerik='Dana köfte, cheddar', icerik_en='Beef patty, cheddar',
             sut='TRUE', gluten='TRUE', gorsel_link='https://lh3.googleusercontent.com/d/BBB'),
        dict(kod='patates', kategori_kodu='atistirmalik', kategori='Atıştırmalık', urun_adi='Patates', fiyat='90'),
        dict(kod='margherita', kategori_kodu='pizzalar', kategori='Pizzalar', urun_adi='Margherita', fiyat='250'),
        dict(kod='pepperoni', kategori_kodu='pizzalar', kategori='Pizzalar', urun_adi='Pepperoni', fiyat='290'),
    ]


class SemaTesti(TestCase):
    def test_sutun_sayilari_ve_sirasi(self):
        self.assertEqual(MARKALAR['geek']['sutunlar'], [
            'kod', 'kategori_kodu', 'kategori', 'kategori_en', 'urun_adi', 'urun_adi_en', 'fiyat', 'aciklama', 'aciklama_en',
            'kalori', 'protein', 'sut', 'yumurta', 'gluten', 'sert_kabuklu_yemis', 'yer_fistigi', 'susam', 'soya', 'hardal',
            'sirke_tursu', 'balik', 'koruyucu_madde', 'vegan', 'sube_notu', 'sube_notu_en', 'gorsel_link'])
        self.assertEqual(MARKALAR['baga']['sutunlar'], [
            'kod', 'kategori_kodu', 'kategori', 'kategori_en', 'urun_adi', 'urun_adi_en', 'fiyat', 'aciklama', 'aciklama_en',
            'icerik', 'icerik_en', 'kalori', 'protein', 'sut', 'yumurta', 'gluten', 'soya',
            'vegan', 'sube_notu', 'sube_notu_en', 'gorsel_link'])

    def test_iki_marka_migration_ile_gelir(self):
        self.assertEqual(list(MenuMarka.objects.values_list('kod', flat=True)), ['geek', 'baga'])


@override_settings(**_AYAR)
class AktarTesti(TestCase):
    def setUp(self):
        self.dizin = tempfile.mkdtemp(prefix='csv_')
        self.addCleanup(shutil.rmtree, self.dizin, True)
        self.geek = self.dizin + '/geek.csv'
        self.baga = self.dizin + '/baga.csv'
        _csv_yaz(self.geek, MARKALAR['geek']['sutunlar'], _geek_satirlari())
        _csv_yaz(self.baga, MARKALAR['baga']['sutunlar'], _baga_satirlari())

    def _calistir(self, marka, dosya, *ek):
        out = io.StringIO()
        call_command('menu_aktar', '--marka', marka, '--dosya', dosya, *ek, stdout=out)
        return out.getvalue()

    def test_kuru_calistirma_hicbir_sey_yazmaz(self):
        cikti = self._calistir('geek', self.geek, '--dry-run')
        self.assertIn('KURU ÇALIŞTIRMA', cikti)
        self.assertEqual(MenuUrun.objects.count(), 0)
        self.assertEqual(MenuKategori.objects.count(), 0)

    def test_geek_aktarimi_ve_idempotentlik(self):
        self._calistir('geek', self.geek)
        geek = MenuMarka.objects.get(kod='geek')
        self.assertEqual(MenuUrun.objects.filter(marka=geek).count(), 3)       # boş adlı satır atlandı
        self.assertEqual(MenuKategori.objects.filter(marka=geek).count(), 9)   # sitedeki 9 sabit kategori
        u = MenuUrun.objects.get(marka=geek, kod='avokado-tost')
        self.assertEqual(str(u.fiyat), '245.50')
        self.assertEqual(str(u.protein), '12.5')
        self.assertTrue(u.gluten and u.sut and not u.vegan)
        self.assertEqual(u.gorsel_harici, 'https://lh3.googleusercontent.com/d/AAA')
        self.assertEqual(u.aciklama, 'Çıtır ekmek,\navokado')
        # eski kod yönlendirmeleri sitedeki gibi
        self.assertEqual(MenuUrun.objects.get(marka=geek, kod='serpme').kategori.kod, 'kahvaltilar')
        self.assertEqual(MenuUrun.objects.get(marka=geek, kod='tavuk-wrap').kategori.kod, 'wrap')
        # tekrar çalıştırınca hiçbir şey değişmez
        onceki = list(MenuUrun.objects.order_by('id').values())
        cikti = self._calistir('geek', self.geek)
        self.assertIn('Yeni ürün           : 0', cikti)
        self.assertEqual(list(MenuUrun.objects.order_by('id').values()), onceki)

    def test_panel_duzenlemesi_guncelle_olmadan_ezilmez(self):
        self._calistir('geek', self.geek)
        u = MenuUrun.objects.get(kod='avokado-tost')
        u.fiyat = 999
        u.save()
        self._calistir('geek', self.geek)
        u.refresh_from_db()
        self.assertEqual(u.fiyat, 999)
        self._calistir('geek', self.geek, '--guncelle')
        u.refresh_from_db()
        self.assertEqual(str(u.fiyat), '245.50')

    def test_baga_pizzalar_raporlanir_ve_canli_davranis_korunur(self):
        cikti = self._calistir('baga', self.baga)
        self.assertIn('SİTEDE TANIMLI DEĞİL', cikti)
        self.assertIn('[pizzalar] 2 ürün', cikti)
        baga = MenuMarka.objects.get(kod='baga')
        self.assertEqual(MenuUrun.objects.filter(marka=baga).count(), 4)
        # bugün aramada çıkıyorlar -> menüde açık kalır, CSV'ye yazılır
        self.assertEqual(MenuUrun.objects.filter(marka=baga, aktif=False).count(), 0)
        _sutunlar, satirlar = csv_satirlari(baga)
        self.assertEqual([s[0] for s in satirlar], ['baga-burger', 'patates', 'margherita', 'pepperoni'])
        b = MenuUrun.objects.get(marka=baga, kod='baga-burger')
        self.assertEqual(b.icerik, 'Dana köfte, cheddar')
        self.assertTrue(b.sut and b.gluten and not b.soya)

    def test_tekrar_eden_kod_urunu_kaybettirmez(self):
        satirlar = _baga_satirlari() + [
            dict(kod='patates', kategori_kodu='atistirmalik', kategori='Atıştırmalık', urun_adi='Patates (Büyük)', fiyat='120')]
        _csv_yaz(self.baga, MARKALAR['baga']['sutunlar'], satirlar)
        cikti = self._calistir('baga', self.baga)
        self.assertIn('patates → patates-2', cikti)
        baga = MenuMarka.objects.get(kod='baga')
        self.assertEqual(MenuUrun.objects.filter(marka=baga).count(), 5)
        self.assertEqual(MenuUrun.objects.get(marka=baga, kod='patates-2').urun_adi, 'Patates (Büyük)')
        # tekrar çalıştırınca yeni ürün oluşmaz (idempotent)
        self._calistir('baga', self.baga)
        self.assertEqual(MenuUrun.objects.filter(marka=baga).count(), 5)


@override_settings(**_AYAR)
class CsvTesti(TestCase):
    def setUp(self):
        d = tempfile.mkdtemp(prefix='csv_')
        self.addCleanup(shutil.rmtree, d, True)
        _csv_yaz(d + '/g.csv', MARKALAR['geek']['sutunlar'], _geek_satirlari())
        _csv_yaz(d + '/b.csv', MARKALAR['baga']['sutunlar'], _baga_satirlari())
        call_command('menu_aktar', '--marka', 'geek', '--dosya', d + '/g.csv', stdout=io.StringIO())
        call_command('menu_aktar', '--marka', 'baga', '--dosya', d + '/b.csv', stdout=io.StringIO())

    def _oku(self, kod):
        marka = MenuMarka.objects.get(kod=kod)
        return list(csv.DictReader(io.StringIO(csv_uret(marka).decode('utf-8')))), csv_uret(marka)

    def test_basliklar_markaya_ozel_ve_birebir(self):
        for kod in ('geek', 'baga'):
            satirlar, ham = self._oku(kod)
            ilk = ham.decode('utf-8').split('\n', 1)[0]
            ek = ['ek_alerjenler', 'ek_alerjenler_en']            # panelden eklenen alerjenler EN SONDA
            self.assertEqual(ilk.split(','), MARKALAR[kod]['sutunlar'] + ek)
            self.assertFalse(ham.startswith(b'\xef\xbb\xbf'))             # BOM yok

    def test_site_gibi_okunabilir_degerler(self):
        satirlar, _ = self._oku('geek')
        s = {r['kod']: r for r in satirlar}
        self.assertEqual(s['avokado-tost']['fiyat'], '245.5')             # parseFloat için nokta
        self.assertEqual(s['avokado-tost']['gluten'], 'TRUE')
        self.assertEqual(s['avokado-tost']['hardal'], 'FALSE')
        self.assertEqual(s['avokado-tost']['aciklama'], 'Çıtır ekmek,\navokado')   # tırnaklı çok satırlı alan
        self.assertEqual(s['serpme']['protein'], '45')
        self.assertEqual(s['serpme']['kalori'], '')
        self.assertEqual(s['serpme']['kategori_kodu'], 'kahvaltilar')
        self.assertEqual(s['serpme']['kategori'], 'Kahvaltılar')

    def test_baga_alerjen_sutunlari_yalniz_dort(self):
        satirlar, _ = self._oku('baga')
        self.assertNotIn('hardal', satirlar[0])
        self.assertIn('icerik', satirlar[0])
        geek, _ = self._oku('geek')
        self.assertNotIn('icerik', geek[0])

    def test_pasif_urun_csvye_yazilmaz(self):
        MenuUrun.objects.filter(kod='serpme').update(aktif=False)
        satirlar, _ = self._oku('geek')
        self.assertNotIn('serpme', [r['kod'] for r in satirlar])


@override_settings(**_AYAR)
class PanelTesti(TestCase):
    def _kullanici(self, rol, ad):
        u = User.objects.create_user(ad, password='x')
        Personel.objects.create(user=u, ad_soyad=ad, rol=rol)
        return u

    def setUp(self):
        d = tempfile.mkdtemp(prefix='csv_')
        self.addCleanup(shutil.rmtree, d, True)
        _csv_yaz(d + '/g.csv', MARKALAR['geek']['sutunlar'], _geek_satirlari())
        _csv_yaz(d + '/b.csv', MARKALAR['baga']['sutunlar'], _baga_satirlari())
        call_command('menu_aktar', '--marka', 'geek', '--dosya', d + '/g.csv', stdout=io.StringIO())
        call_command('menu_aktar', '--marka', 'baga', '--dosya', d + '/b.csv', stdout=io.StringIO())
        self.gm = self._kullanici(Rol.GENEL_MUDUR, 'gm')

    def test_yetki(self):
        for rol in (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI):
            self.client.force_login(self._kullanici(rol, 'u_' + rol))
            self.assertEqual(self.client.get(reverse('menu_yonetim')).status_code, 200, rol)
            self.assertEqual(self.client.get(reverse('menu_urunler', args=['baga'])).status_code, 200, rol)
            self.assertEqual(self.client.get(reverse('menu_urunler', args=['geek'])).status_code, 200, rol)
        for rol in (Rol.MUDUR, Rol.MAGAZA_MUDURU, Rol.SATIN_ALMA, Rol.SEVKIYAT, Rol.EGITMEN, Rol.SEF,
                    Rol.MUTFAK_SORUMLUSU, Rol.PERSONEL):
            u = self._kullanici(rol, 'x_' + rol)
            self.client.force_login(u)
            for url in (reverse('menu_yonetim'), reverse('menu_urunler', args=['baga']),
                        reverse('menu_kategoriler', args=['geek']), reverse('menu_urun_yeni', args=['geek'])):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 302, '%s %s' % (rol, url))
            r = self.client.post(reverse('menu_urunler', args=['geek']), {'islem': 'toplu_kaydet'})
            self.assertEqual(r.status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('menu_yonetim')).status_code, 302)

    def test_nav_baglantisi_yalniz_yetkililere(self):
        link = 'href="%s"' % reverse('menu_yonetim')
        for rol in (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI):
            self.client.force_login(self._kullanici(rol, 'n_' + rol))
            r = self.client.get(reverse('ana_sayfa'), follow=True)
            self.assertContains(r, link, msg_prefix=rol)
        for rol in (Rol.MUDUR, Rol.SEF, Rol.PERSONEL, Rol.SATIN_ALMA, Rol.EGITMEN):
            self.client.force_login(self._kullanici(rol, 'm_' + rol))
            r = self.client.get(reverse('ana_sayfa'), follow=True)
            self.assertNotContains(r, link, msg_prefix=rol)

    def test_toplu_fiyat_ve_gizleme(self):
        self.client.force_login(self.gm)
        u = MenuUrun.objects.get(kod='avokado-tost')
        s = MenuUrun.objects.get(kod='serpme')
        r = self.client.post(reverse('menu_urunler', args=['geek']), {
            'islem': 'toplu_kaydet', 'id': [u.id, s.id],
            'fiyat_%d' % u.id: '260,00', 'aktif_%d' % u.id: 'on',
            'fiyat_%d' % s.id: '450',                                       # aktif kutusu yok -> gizlenir
        })
        self.assertEqual(r.status_code, 302)
        u.refresh_from_db(); s.refresh_from_db()
        self.assertEqual(str(u.fiyat), '260.00')
        self.assertFalse(s.aktif)
        dosya = open(_TMP + '/menu/geek.csv', encoding='utf-8').read()
        self.assertIn('avokado-tost,tost,Tostlar,Toasts,Avokado Tost,Avocado Toast,260,', dosya)
        self.assertNotIn('serpme', dosya)

    def test_urun_ekle_fotograf_kucultulur_ve_yayinlanir(self):
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (3000, 2000), (200, 30, 30)).save(buf, 'JPEG')
        self.client.force_login(self.gm)
        kat = MenuKategori.objects.get(marka__kod='geek', kod='bowl')
        r = self.client.post(reverse('menu_urun_yeni', args=['geek']), {
            'kategori': kat.id, 'urun_adi': 'Çıtır Bowl', 'urun_adi_en': 'Crispy Bowl', 'fiyat': '1.250,50',
            'kalori': '500', 'protein': '41,5', 'susam': 'on', 'vegan': 'on', 'aktif': 'on',
            'foto': SimpleUploadedFile('buyuk.jpg', buf.getvalue(), content_type='image/jpeg'),
        })
        self.assertEqual(r.status_code, 302, getattr(r, 'context', None) and r.context['form'].errors)
        u = MenuUrun.objects.get(marka__kod='geek', kod='citir-bowl')
        self.assertEqual(str(u.fiyat), '1250.50')
        self.assertTrue(u.susam and u.vegan and not u.sut)
        self.assertEqual(u.sira, 10)
        im = Image.open(u.gorsel.path)
        self.assertLessEqual(max(im.size), 1200)
        csv_metni = open(_TMP + '/menu/geek.csv', encoding='utf-8').read()
        self.assertIn('citir-bowl,bowl,', csv_metni)
        self.assertIn(u.gorsel.url, csv_metni)
        self.assertIn(',1250.5,', csv_metni)

    def test_secilen_fotograf_ulasmadiysa_kaydedilmez_ve_basarili_demez(self):
        self.client.force_login(self.gm)
        kat = MenuKategori.objects.get(marka__kod='geek', kod='bowl')
        r = self.client.post(reverse('menu_urun_yeni', args=['geek']), {
            'kategori': kat.id, 'urun_adi': 'Fotosuz Bowl', 'fiyat': '100', 'aktif': 'on', 'foto_secildi': '1'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'sunucuya ulaşmadı')
        self.assertFalse(MenuUrun.objects.filter(urun_adi='Fotosuz Bowl').exists())

    def test_fotograf_yuklenince_basari_mesaji_bunu_soyler(self):
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (800, 600), (30, 30, 200)).save(buf, 'JPEG')
        self.client.force_login(self.gm)
        kat = MenuKategori.objects.get(marka__kod='geek', kod='bowl')
        r = self.client.post(reverse('menu_urun_yeni', args=['geek']), {
            'kategori': kat.id, 'urun_adi': 'Fotolu Bowl', 'fiyat': '100', 'aktif': 'on', 'foto_secildi': '1',
            'foto': SimpleUploadedFile('f.jpg', buf.getvalue(), content_type='image/jpeg')}, follow=True)
        self.assertContains(r, 'Fotoğraf yüklendi.')
        self.assertTrue(MenuUrun.objects.get(urun_adi='Fotolu Bowl').gorsel)

    def test_mevcut_fotograf_degistirilince_yeni_dosya_silinmez(self):
        """Hata: eski FieldFile ile yeni aynı nesneydi, yeni yüklenen dosya siliniyordu."""
        from PIL import Image

        def jpg(renk):
            b = io.BytesIO(); Image.new('RGB', (400, 300), renk).save(b, 'JPEG'); return b.getvalue()
        self.client.force_login(self.gm)
        kat = MenuKategori.objects.get(marka__kod='geek', kod='bowl')
        self.client.post(reverse('menu_urun_yeni', args=['geek']), {
            'kategori': kat.id, 'urun_adi': 'Degisen Bowl', 'fiyat': '100', 'aktif': 'on', 'foto_secildi': '1',
            'foto': SimpleUploadedFile('a.jpg', jpg((200, 0, 0)), content_type='image/jpeg')})
        u = MenuUrun.objects.get(urun_adi='Degisen Bowl')
        eski = u.gorsel.name
        r = self.client.post(reverse('menu_urun_duzenle', args=['geek', u.id]), {
            'kategori': kat.id, 'urun_adi': 'Degisen Bowl', 'fiyat': '100', 'aktif': 'on', 'foto_secildi': '1',
            'foto': SimpleUploadedFile('b.jpg', jpg((0, 0, 200)), content_type='image/jpeg')}, follow=True)
        self.assertContains(r, 'Fotoğraf yüklendi.')
        u.refresh_from_db()
        self.assertNotEqual(u.gorsel.name, eski)
        self.assertTrue(u.gorsel.storage.exists(u.gorsel.name), 'yeni dosya silinmemeli')
        self.assertFalse(u.gorsel.storage.exists(eski), 'eski dosya temizlenmeli')
        u.gorsel.storage.delete(u.gorsel.name)

    def test_ayni_kod_reddedilir_ve_baga_formu_geek_alerjenlerini_icermez(self):
        self.client.force_login(self.gm)
        kat = MenuKategori.objects.get(marka__kod='geek', kod='tost')
        r = self.client.post(reverse('menu_urun_yeni', args=['geek']), {
            'kategori': kat.id, 'urun_adi': 'Avokado Tost', 'fiyat': '10', 'aktif': 'on'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('kod', r.context['form'].errors)
        r = self.client.get(reverse('menu_urun_yeni', args=['baga']))
        alanlar = set(r.context['form'].fields)
        self.assertIn('icerik', alanlar)
        self.assertTrue({'sut', 'yumurta', 'gluten', 'soya'} <= alanlar)
        self.assertFalse({'hardal', 'susam', 'balik', 'koruyucu_madde'} & alanlar)
        r = self.client.get(reverse('menu_urun_yeni', args=['geek']))
        self.assertNotIn('icerik', r.context['form'].fields)
        self.assertIn('hardal', r.context['form'].fields)

    def test_sil_ve_kayit_yayin_hatasinda_geri_alinmaz(self):
        self.client.force_login(self.gm)
        u = MenuUrun.objects.get(kod='serpme')
        with mock.patch('panel.menu_yayin.dosyaya_yaz', side_effect=OSError('R2 erişilemiyor')):
            r = self.client.post(reverse('menu_urun_duzenle', args=['geek', u.id]), {'islem': 'sil'}, follow=True)
        self.assertFalse(MenuUrun.objects.filter(pk=u.pk).exists())           # silme geri alınmadı
        self.assertContains(r, 'YAYINLANAMADI')
        self.assertContains(r, 'R2 erişilemiyor')
        self.assertIn('R2 erişilemiyor', MenuMarka.objects.get(kod='geek').son_yayin_hata)
        # düzelince yeniden yayınla
        r = self.client.post(reverse('menu_yayinla', args=['geek']), follow=True)
        self.assertEqual(MenuMarka.objects.get(kod='geek').son_yayin_hata, '')
        self.assertIsNotNone(MenuMarka.objects.get(kod='geek').son_yayin)

    def test_kategori_islemleri(self):
        self.client.force_login(self.gm)
        url = reverse('menu_kategoriler', args=['baga'])
        r = self.client.post(url, {'islem': 'ekle', 'kod': 'Piz-za', 'ad': 'X'}, follow=True)
        self.assertFalse(MenuKategori.objects.filter(marka__kod='baga', kod__in=['Piz-za', 'piz-za']).exists())
        r = self.client.post(url, {'islem': 'ekle', 'kod': 'icecekler', 'ad': 'İçecekler', 'ad_en': 'Drinks'}, follow=True)
        self.assertContains(r, 'sitede görünmez')
        k = MenuKategori.objects.get(marka__kod='baga', kod='icecekler')
        self.client.post(url, {'islem': 'sil', 'kat_id': k.id})
        self.assertFalse(MenuKategori.objects.filter(pk=k.pk).exists())
        # ürünü olan kategori silinemez
        h = MenuKategori.objects.get(marka__kod='baga', kod='hamburgerler')
        self.client.post(url, {'islem': 'sil', 'kat_id': h.id})
        self.assertTrue(MenuKategori.objects.filter(pk=h.pk).exists())
        # ad değişir, kod değişmez
        self.client.post(url, {'islem': 'kaydet', 'kat_id': h.id, 'ad': 'Burgerler', 'ad_en': 'Burgers!'})
        h.refresh_from_db()
        self.assertEqual((h.kod, h.ad), ('hamburgerler', 'Burgerler'))
        self.assertIn('hamburgerler,Burgerler,Burgers!', open(_TMP + '/menu/baga.csv', encoding='utf-8').read())
        # sıralama
        a = MenuKategori.objects.get(marka__kod='baga', kod='atistirmalik')
        once = list(MenuKategori.objects.filter(marka__kod='baga').values_list('kod', flat=True))
        self.client.post(url, {'islem': 'sirala', 'kat_id': a.id, 'yon': 'yukari'})
        sonra = list(MenuKategori.objects.filter(marka__kod='baga').values_list('kod', flat=True))
        self.assertEqual(sonra[0], 'atistirmalik')
        self.assertNotEqual(once, sonra)

    def test_urun_siralama(self):
        self.client.force_login(self.gm)
        kat = MenuKategori.objects.get(marka__kod='geek', kod='tost')
        for ad in ('A Tost', 'B Tost'):
            MenuUrun.objects.create(marka=kat.marka, kategori=kat, kod=ad[0].lower() + '-tost', urun_adi=ad, fiyat=1, sira=0)
        ids = list(MenuUrun.objects.filter(kategori=kat).order_by('sira', 'id').values_list('kod', flat=True))
        son = MenuUrun.objects.get(kod=ids[-1])
        self.client.post(reverse('menu_urunler', args=['geek']), {'islem': 'sirala', 'urun_id': son.id, 'yon': 'yukari'})
        yeni = list(MenuUrun.objects.filter(kategori=kat).order_by('sira', 'id').values_list('kod', flat=True))
        self.assertEqual(yeni[-2], ids[-1])


@override_settings(**_AYAR)
class AlerjenYonetimiTesti(PanelTesti):
    """Alerjen listesi: ekle, menüden kaldır/geri al, sil; form ve CSV'ye etkisi."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.gm)
        self.geek = MenuMarka.objects.get(kod='geek')
        self.url = reverse('menu_alerjenler', args=['geek'])
        self.urun = MenuUrun.objects.get(marka=self.geek, kod='avokado-tost')

    def csv(self, kod='geek'):
        m = MenuMarka.objects.get(kod=kod)
        return {r['kod']: r for r in csv.DictReader(io.StringIO(csv_uret(m).decode('utf-8')))}

    def post(self, **v):
        return self.client.post(self.url, v, follow=True)

    def test_sayfa_acilir_ve_sistem_alerjenleri_olusur(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['alerjenler']), 11)
        r = self.client.get(reverse('menu_alerjenler', args=['baga']))
        self.assertEqual(len(r.context['alerjenler']), 4)

    def test_yeni_alerjen_forma_ve_csvye_gider(self):
        self.post(islem='ekle', ad='Kereviz', ad_en='Celery')
        a = self.geek.alerjenler.get(kod='kereviz')
        self.assertFalse(a.sistem)
        r = self.client.get(reverse('menu_urun_duzenle', args=['geek', self.urun.id]))
        self.assertContains(r, 'Kereviz')
        self.client.post(reverse('menu_urun_duzenle', args=['geek', self.urun.id]), {
            'kategori': self.urun.kategori_id, 'urun_adi': self.urun.urun_adi, 'fiyat': '245,50',
            'aktif': 'on', 'ek_alerjenler': ['kereviz']})
        self.urun.refresh_from_db()
        self.assertEqual(self.urun.ek_alerjenler, ['kereviz'])
        satir = self.csv()['avokado-tost']
        self.assertEqual((satir['ek_alerjenler'], satir['ek_alerjenler_en']), ('Kereviz', 'Celery'))

    def test_ayni_alerjen_iki_kez_eklenmez(self):
        self.post(islem='ekle', ad='Kereviz')
        r = self.post(islem='ekle', ad='kereviz')
        self.assertContains(r, 'zaten listede')
        r = self.post(islem='ekle', ad='Süt')
        self.assertContains(r, 'zaten listede')

    def test_sistem_alerjeni_kaldirilinca_formdan_ve_csvden_cikar_geri_alinca_doner(self):
        self.assertEqual(self.csv()['avokado-tost']['gluten'], 'TRUE')
        a = self.geek.alerjenler.get(kod='gluten') if self.geek.alerjenler.exists() else None
        self.client.get(self.url)                                   # satırları oluşturur
        a = self.geek.alerjenler.get(kod='gluten')
        self.post(islem='degistir', alerjen_id=a.id)
        self.assertEqual(self.csv()['avokado-tost']['gluten'], 'FALSE')
        r = self.client.get(reverse('menu_urun_duzenle', args=['geek', self.urun.id]))
        self.assertNotIn('gluten', r.context['form'].fields)
        self.urun.refresh_from_db()
        self.assertTrue(self.urun.gluten)                           # veri silinmedi
        self.post(islem='degistir', alerjen_id=a.id)
        self.assertEqual(self.csv()['avokado-tost']['gluten'], 'TRUE')

    def test_sistem_alerjeni_silinemez_adi_degismez(self):
        self.client.get(self.url)
        a = self.geek.alerjenler.get(kod='sut')
        self.post(islem='sil', alerjen_id=a.id)
        self.post(islem='kaydet', alerjen_id=a.id, ad='Başka')
        a.refresh_from_db()
        self.assertEqual(a.ad, 'Süt')

    def test_ek_alerjen_silinince_urunlerden_temizlenir(self):
        self.post(islem='ekle', ad='Kereviz')
        MenuUrun.objects.filter(pk=self.urun.pk).update(ek_alerjenler=['kereviz'])
        self.post(islem='sil', alerjen_id=self.geek.alerjenler.get(kod='kereviz').id)
        self.urun.refresh_from_db()
        self.assertEqual(self.urun.ek_alerjenler, [])
        self.assertFalse(self.geek.alerjenler.filter(kod='kereviz').exists())

    def test_pasif_ek_alerjen_isareti_korunur(self):
        self.post(islem='ekle', ad='Kereviz')
        a = self.geek.alerjenler.get(kod='kereviz')
        MenuUrun.objects.filter(pk=self.urun.pk).update(ek_alerjenler=['kereviz'])
        self.post(islem='degistir', alerjen_id=a.id)               # kaldır
        self.assertEqual(self.csv()['avokado-tost']['ek_alerjenler'], '')
        self.post(islem='ekle', ad='Lupin')
        self.client.post(reverse('menu_urun_duzenle', args=['geek', self.urun.id]), {
            'kategori': self.urun.kategori_id, 'urun_adi': self.urun.urun_adi, 'fiyat': '245,50',
            'aktif': 'on', 'ek_alerjenler': ['lupin']})
        self.urun.refresh_from_db()
        self.assertEqual(sorted(self.urun.ek_alerjenler), ['kereviz', 'lupin'])
        self.post(islem='degistir', alerjen_id=a.id)               # geri al
        self.assertEqual(self.csv()['avokado-tost']['ek_alerjenler'], 'Kereviz, Lupin')

    def test_yetkisiz_rol_giremez(self):
        self.client.force_login(self._kullanici(Rol.SEF, 'sef_x'))
        self.assertEqual(self.client.get(self.url).status_code, 302)


@override_settings(**_AYAR)
class AcilisGorseliTesti(PanelTesti):
    """QR açılış görseli: yükleme, ayar, sıra, tarih, JSON yayını, yetki."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.gm)
        self.url = reverse('menu_acilis', args=['geek'])
        self.yazilan = {}
        p = mock.patch('panel.menu_acilis.dosyaya_yaz', side_effect=lambda a, i, t=None, **k: self.yazilan.__setitem__(a, i))
        p.start()
        self.addCleanup(p.stop)

    def png(self, ad='a.png', boyut=(40, 70)):
        from PIL import Image
        b = io.BytesIO()
        Image.new('RGB', boyut, (200, 30, 30)).save(b, 'PNG')
        return SimpleUploadedFile(ad, b.getvalue(), content_type='image/png')

    def json(self):
        import json
        return json.loads(self.yazilan['menu/geek-acilis.json'].decode('utf-8'))

    def test_sayfa_ve_yetki(self):
        for kod in ('geek', 'baga'):
            self.assertEqual(self.client.get(reverse('menu_acilis', args=[kod])).status_code, 200)
        self.client.force_login(self._kullanici(Rol.SEF, 'sef_a'))
        self.assertEqual(self.client.get(self.url).status_code, 302)
        r = self.client.post(self.url, {'islem': 'ayar', 'sure_sn': '3'})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(self.yazilan)

    def test_yukle_ayar_ve_json(self):
        r = self.client.post(self.url, {'islem': 'yukle', 'dosya_secildi': '1', 'dosyalar': [self.png('bir.png'), self.png('iki.png')]}, follow=True)
        self.assertContains(r, '2 görsel eklendi')
        v = self.json()
        self.assertEqual(len(v['gorseller']), 2)
        self.assertEqual(v['sure_sn'], 5)
        self.assertTrue(v['aktif'])
        eski = v['surum']
        self.client.post(self.url, {'islem': 'ayar', 'sure_sn': '8', 'aktif': 'on', 'gunde_bir': 'on'})
        v = self.json()
        self.assertEqual((v['sure_sn'], v['gunde_bir'], v['atlanabilir']), (8, True, False))
        self.assertNotEqual(v['surum'], eski)
        self.client.post(self.url, {'islem': 'ayar', 'sure_sn': '8'})
        self.assertFalse(self.json()['aktif'])

    def test_gecersiz_sure_ve_dosya(self):
        r = self.client.post(self.url, {'islem': 'ayar', 'sure_sn': '60'}, follow=True)
        self.assertContains(r, 'arasında olmalı')
        self.assertFalse(self.yazilan)
        bozuk = SimpleUploadedFile('x.png', b'degil-resim', content_type='image/png')
        r = self.client.post(self.url, {'islem': 'yukle', 'dosya_secildi': '1', 'dosyalar': [bozuk]}, follow=True)
        self.assertContains(r, 'geçerli bir görsel değil')
        r = self.client.post(self.url, {'islem': 'yukle', 'dosya_secildi': '1'}, follow=True)
        self.assertContains(r, 'sunucuya ulaşmadı')

    def test_sira_tarih_ve_silme(self):
        self.client.post(self.url, {'islem': 'yukle', 'dosya_secildi': '1', 'dosyalar': [self.png('a.png'), self.png('b.png')]})
        a, b = list(MenuMarka.objects.get(kod='geek').acilis_gorselleri.order_by('sira'))
        self.client.post(self.url, {'islem': 'asagi', 'id': a.id})
        self.assertEqual([g['baslik'] for g in self.json()['gorseller']], ['b', 'a'])
        self.client.post(self.url, {'islem': 'gorsel', 'id': a.id, 'baslik': 'Yaz', 'aktif': 'on',
                                    'baslangic': '2026-12-01', 'bitis': '2026-12-31'})
        g = [x for x in self.json()['gorseller'] if x['baslik'] == 'Yaz'][0]
        self.assertEqual((g['baslangic'], g['bitis']), ('2026-12-01', '2026-12-31'))
        r = self.client.post(self.url, {'islem': 'gorsel', 'id': a.id, 'baslik': 'Yaz', 'aktif': 'on',
                                        'baslangic': '2026-12-31', 'bitis': '2026-12-01'}, follow=True)
        self.assertContains(r, 'önce olamaz')
        self.client.post(self.url, {'islem': 'gorsel', 'id': b.id, 'baslik': 'b'})
        self.assertEqual([x['baslik'] for x in self.json()['gorseller']], ['Yaz'])
        self.client.post(self.url, {'islem': 'sil', 'id': a.id})
        self.assertEqual(self.json()['gorseller'], [])

    def test_yukleme_siniri_ve_marka_ayrimi(self):
        self.client.post(self.url, {'islem': 'yukle', 'dosya_secildi': '1', 'dosyalar': [self.png('%d.png' % i) for i in range(10)]})
        self.assertEqual(MenuMarka.objects.get(kod='geek').acilis_gorselleri.count(), 8)
        self.assertEqual(MenuMarka.objects.get(kod='baga').acilis_gorselleri.count(), 0)

    def test_yayin_hatasi_kaydedilir(self):
        with mock.patch('panel.menu_acilis.dosyaya_yaz', side_effect=OSError('R2 yok')):
            r = self.client.post(self.url, {'islem': 'yayinla'}, follow=True)
        self.assertContains(r, 'R2 yok')
        self.assertIn('R2 yok', MenuMarka.objects.get(kod='geek').acilis_yayin_hata)


@override_settings(**_AYAR)
class SubeBazliMenuTesti(PanelTesti):
    """Şube listesi, ürün×şube müsaitliği ve yayın JSON'u."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.gm)
        self.geek = MenuMarka.objects.get(kod='geek')
        self.url = reverse('menu_subeler', args=['geek'])
        self.yazilan = {}
        from . import menu_yayin
        gercek = menu_yayin.dosyaya_yaz        # PanelTesti'nden miras testler dosyayı diskten okur: yazmaya devam et

        def yaz(anahtar, icerik, tip='text/csv; charset=utf-8', **k):
            self.yazilan[anahtar] = icerik
            return gercek(anahtar, icerik, tip)
        p = mock.patch('panel.menu_yayin.dosyaya_yaz', side_effect=yaz)
        p.start()
        self.addCleanup(p.stop)

    def json(self):
        import json
        return json.loads(self.yazilan['menu/geek-subeler.json'].decode('utf-8'))

    def test_sayfa_yetki_ve_bos_liste(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.get(reverse('menu_subeler', args=['baga'])).status_code, 200)
        self.client.force_login(self._kullanici(Rol.SEF, 'sef_s'))
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertEqual(self.client.post(self.url, {'islem': 'ekle', 'ad': 'X'}).status_code, 302)
        self.assertFalse(self.yazilan)

    def test_sube_ekle_sirala_sil(self):
        r = self.client.post(self.url, {'islem': 'ekle', 'ad': 'İncilipınar Şubesi'}, follow=True)
        self.assertContains(r, '1 şube eklendi')
        self.client.post(self.url, {'islem': 'ekle', 'ad': 'Sanko'})
        self.client.post(self.url, {'islem': 'ekle', 'ad': 'sanko'})            # aynı ad: eklenmez
        a, b = list(self.geek.menu_subeleri.all())
        self.assertEqual((a.kod, b.kod), ('incilipinar-subesi', 'sanko'))
        self.client.post(self.url, {'islem': 'asagi', 'id': a.id})
        self.assertEqual([s['ad'] for s in self.json()['subeler']], ['Sanko', 'İncilipınar Şubesi'])
        self.client.post(self.url, {'islem': 'duzenle', 'id': b.id, 'ad': 'Sanko AVM'})   # aktif işaretsiz → kapalı
        self.assertEqual([s['kod'] for s in self.json()['subeler']], ['incilipinar-subesi'])
        self.client.post(self.url, {'islem': 'sil', 'id': a.id})
        self.assertEqual(self.json()['subeler'], [])

    def test_matris_gizler_ve_json_yazar(self):
        for ad in ('A Şube', 'B Şube'):
            self.client.post(self.url, {'islem': 'ekle', 'ad': ad})
        sa, sb = list(self.geek.menu_subeleri.all())
        urunler = list(MenuUrun.objects.filter(marka=self.geek)[:2])
        u1, u2 = urunler
        veri = {'islem': 'matris', 'urun_ids': [u1.id, u2.id]}
        veri['v_%d_%d' % (u1.id, sa.id)] = 'on'; veri['v_%d_%d' % (u1.id, sb.id)] = 'on'
        veri['v_%d_%d' % (u2.id, sa.id)] = 'on'            # u2 B şubede işaretsiz → gizli
        self.client.post(self.url, veri)
        j = self.json()
        self.assertEqual(j['yok'], {u2.kod: [sb.kod]})
        self.assertEqual(sorted(s['kod'] for s in j['subeler']), sorted([sa.kod, sb.kod]))
        self.assertTrue(j['surum'])
        # CSV şeması değişmedi, ürün hâlâ CSV'de
        self.assertIn(u2.kod, [r['kod'] for r in csv.DictReader(io.StringIO(csv_uret(self.geek).decode('utf-8')))])
        # geri aç
        veri['v_%d_%d' % (u2.id, sb.id)] = 'on'
        self.client.post(self.url, veri)
        self.assertEqual(self.json()['yok'], {})

    def test_gorunmeyen_urun_secimi_korunur_ve_baga_ayri(self):
        self.client.post(self.url, {'islem': 'ekle', 'ad': 'A Şube'})
        s = self.geek.menu_subeleri.get()
        u1, u2 = list(MenuUrun.objects.filter(marka=self.geek)[:2])
        s.gizli_urunler.add(u2)
        self.client.post(self.url, {'islem': 'matris', 'urun_ids': [u1.id], 'v_%d_%d' % (u1.id, s.id): 'on'})
        self.assertEqual(list(s.gizli_urunler.all()), [u2])            # formda olmayan ürüne dokunulmadı
        baga = MenuMarka.objects.get(kod='baga')
        self.assertEqual(baga.menu_subeleri.count(), 0)

    def test_urun_yayininda_json_de_yenilenir_ve_hata_gorunur(self):
        self.client.post(self.url, {'islem': 'ekle', 'ad': 'A Şube'})
        self.yazilan.clear()
        from .menu_yayin import yayinla
        self.assertEqual(yayinla(self.geek), (True, ''))
        self.assertIn('menu/geek-subeler.json', self.yazilan)
        self.assertIn('menu/geek.csv', self.yazilan)
        def bozuk(anahtar, icerik, tip='x', **k):
            if anahtar.endswith('-subeler.json'):
                raise OSError('R2 yok')
        with mock.patch('panel.menu_yayin.dosyaya_yaz', side_effect=bozuk):
            ok, hata = yayinla(self.geek)
        self.assertFalse(ok)
        self.assertIn('Şube listesi', hata)

    def test_panel_subesinden_ekleme(self):
        from .models import Sube
        ps = Sube.objects.create(ad='Panel Şubesi')
        r = self.client.get(self.url)
        self.assertContains(r, 'Panel Şubesi')
        self.client.post(self.url, {'islem': 'ekle', 'panel_sube': [ps.id]})
        self.assertEqual(self.geek.menu_subeleri.get().ad, 'Panel Şubesi')
        self.assertNotContains(self.client.get(self.url), 'name="panel_sube"')


@override_settings(**_AYAR)
class BolgeMuduruYetkiTesti(PanelTesti):
    """Ekip sayfasından Bölge Müdürüne QR Menü / Geri Bildirim Yönetimi yetkisi verme-alma."""

    def setUp(self):
        super().setUp()
        self.bm = self._kullanici(Rol.MUDUR, 'bm1')
        self.bm_p = self.bm.personel
        self.ekip = reverse('ekip')

    def test_varsayilan_erisim_yok(self):
        self.client.force_login(self.bm)
        self.assertEqual(self.client.get(reverse('menu_yonetim')).status_code, 302)
        self.assertEqual(self.client.get(reverse('geri_bildirim_yonetim')).status_code, 302)

    def test_menu_yetkisi_ver_al(self):
        for rol in (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI):
            self.client.force_login(self._kullanici(rol, 'v_' + rol))
            self.assertContains(self.client.get(self.ekip), 'QR Menü Yönetimi Yetkisi')
            self.client.post(self.ekip, {'islem': 'menu_yetki_ekle', 'personel_id': self.bm_p.id})
            self.bm_p.refresh_from_db()
            self.assertTrue(self.bm_p.menu_yetkilisi, rol)
            self.client.post(self.ekip, {'islem': 'menu_yetki_cikar', 'personel_id': self.bm_p.id})
            self.bm_p.refresh_from_db()
            self.assertFalse(self.bm_p.menu_yetkilisi, rol)

    def test_yetkili_bm_menuye_girer_digerleri_giremez(self):
        self.client.force_login(self.gm)
        self.client.post(self.ekip, {'islem': 'menu_yetki_ekle', 'personel_id': self.bm_p.id})
        self.client.force_login(self.bm)
        for ad, arg in (('menu_yonetim', []), ('menu_urunler', ['geek']), ('menu_acilis', ['geek']), ('menu_subeler', ['baga'])):
            self.assertEqual(self.client.get(reverse(ad, args=arg)).status_code, 200, ad)
        r = self.client.get(reverse('ana_sayfa'), follow=True)
        self.assertContains(r, 'href="%s"' % reverse('menu_yonetim'))
        self.assertNotContains(r, 'href="%s"' % reverse('geri_bildirim_yonetim'))   # geri bildirim ayrı yetki
        self.client.force_login(self._kullanici(Rol.MUDUR, 'bm2'))
        self.assertEqual(self.client.get(reverse('menu_yonetim')).status_code, 302)

    def test_geri_bildirim_yetkisi_ve_yatirimci_gorur(self):
        self.client.force_login(self.gm)
        self.client.post(self.ekip, {'islem': 'gb_yetki_ekle', 'personel_id': self.bm_p.id})
        self.client.force_login(self.bm)
        self.assertEqual(self.client.get(reverse('geri_bildirim_yonetim')).status_code, 200)
        r = self.client.get(reverse('ana_sayfa'), follow=True)
        self.assertContains(r, 'href="%s"' % reverse('geri_bildirim_yonetim'))
        self.assertNotContains(r, 'href="%s"' % reverse('menu_yonetim'))
        self.client.force_login(self._kullanici(Rol.YATIRIMCI, 'yat_gb'))
        self.assertEqual(self.client.get(reverse('geri_bildirim_yonetim')).status_code, 200)
        self.client.force_login(self.gm)
        self.client.post(self.ekip, {'islem': 'gb_yetki_cikar', 'personel_id': self.bm_p.id})
        self.client.force_login(self.bm)
        self.assertEqual(self.client.get(reverse('geri_bildirim_yonetim')).status_code, 302)

    def test_yetki_sadece_bolge_mudurune_verilir_ve_yetkisiz_veremez(self):
        sef = self._kullanici(Rol.SEF, 'sef_y').personel
        self.client.force_login(self.gm)
        self.client.post(self.ekip, {'islem': 'menu_yetki_ekle', 'personel_id': sef.id})
        sef.refresh_from_db()
        self.assertFalse(sef.menu_yetkilisi)
        self.client.force_login(self.bm)                 # bölge müdürü kendine yetki veremez (ekip sayfası kapalı)
        self.client.post(self.ekip, {'islem': 'menu_yetki_ekle', 'personel_id': self.bm_p.id})
        self.bm_p.refresh_from_db()
        self.assertFalse(self.bm_p.menu_yetkilisi)
