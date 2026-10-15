"""Temizlik malzemesi tüketimi:  python manage.py test panel.tests_temizlik"""
import datetime
import io
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import temizlik as tz
from .models import (Rol, SevkiyatKalem, SevkiyatTalep, Sube, TemizlikDuzeltme, TemizlikSayim, TemizlikUrun)
from .tests_mola_stok import _AYAR, kisi

AY = datetime.date(2026, 9, 1)
D = datetime.date


def _zaman(gun):
    return timezone.make_aware(datetime.datetime.combine(gun, datetime.time(12, 0)))


@override_settings(**_AYAR)
class TemizlikTestleri(TestCase):
    def setUp(self):
        self.merkez = Sube.objects.create(ad='Merkez')
        self.diger = Sube.objects.create(ad='Diğer')
        self.sef = kisi(Rol.SEF, self.merkez, 'Şef Ayşe')
        self.sef2 = kisi(Rol.SEF, self.diger, 'Şef Diğer')
        self.gm = kisi(Rol.GENEL_MUDUR, None, 'GM')
        self.sa = kisi(Rol.SATIN_ALMA, None, 'Satın Alma')
        self.pers = kisi(Rol.PERSONEL, self.merkez, 'Personel')
        self.urun = TemizlikUrun.objects.get(ad='CAM SİL 500 ML')      # koli içeriği 20 (göç ile yüklendi)
        self.baska = TemizlikUrun.objects.get(ad='MOP BEZİ')

    def sevkiyat(self, sube, gun, adet_koli=1, urun=None):
        urun = urun or self.urun
        t = SevkiyatTalep.objects.create(sube=sube, durum='Teslim Edildi')
        SevkiyatTalep.objects.filter(pk=t.pk).update(onay_tarih=_zaman(gun))
        SevkiyatKalem.objects.create(talep=t, urun=None, urun_ad=urun.ad, form='TEMIZLIK', koli_icerigi=20,
                                     istenen_miktar=adet_koli, istenen_birim='KOLİ',
                                     sevkiyat_miktar=adet_koli, sevkiyat_birim='KOLİ')

    def kaydet(self, kisi_, tur, tarih, deger, sube=None, urun=None, koli='', acik=''):
        """Sayım sayfasına POST (tur: 'ilk' | 'son'); deger = kapalı adet kutusu."""
        self.client.force_login(kisi_.user)
        urun = urun or self.urun
        veri = {'ay': '2026-09', 'tarih': tarih, 'adet_%d' % urun.id: deger,
                'koli_%d' % urun.id: koli, 'acik_%d' % urun.id: acik}
        if sube:
            veri['sube'] = sube.id
        return self.client.post(reverse('temizlik_sayim', args=[tur]), veri)

    def hesap(self, sube=None):
        v = tz.veri_hesapla([sube or self.merkez], AY, bugun=D(2026, 10, 5))
        return v, next(r for r in v['toplam'] if r['urun'].id == self.urun.id)

    # ---- veri
    def test_excel_urunleri_yuklendi(self):
        self.assertEqual(TemizlikUrun.objects.count(), 43)
        self.assertEqual(self.urun.koli_icerigi, 20)

    # ---- hesap
    def test_kullanim_formulu(self):
        self.sevkiyat(self.merkez, D(2026, 9, 5), 1)     # 20 adet
        self.sevkiyat(self.merkez, D(2026, 9, 14), 2)    # 40 adet
        self.kaydet(self.sef, 'ilk', '2026-08-31', '10')
        self.kaydet(self.sef, 'son', '2026-09-28', '4')
        _, r = self.hesap()
        self.assertEqual((r['ilk'], r['ilave'], r['son']), (Decimal('10'), Decimal('60'), Decimal('4')))
        self.assertEqual(r['kullanim'], Decimal('66'))   # 10 + 60 - 4

    def test_sayim_gununden_onceki_ve_sonraki_sevkiyat_sayilmaz(self):
        self.sevkiyat(self.merkez, D(2026, 8, 30))        # ilk sayımdan önce
        self.sevkiyat(self.merkez, D(2026, 8, 31))        # ilk sayım günü -> bir sonraki döneme girer
        self.sevkiyat(self.merkez, D(2026, 9, 28))        # son sayım günü -> bu döneme girer
        self.sevkiyat(self.merkez, D(2026, 9, 29))        # son sayımdan sonra
        self.kaydet(self.sef, 'ilk', '2026-08-31', '0')
        self.kaydet(self.sef, 'son', '2026-09-28', '0')
        _, r = self.hesap()
        self.assertEqual(r['ilave'], Decimal('20'))

    def test_baska_sube_ve_onaysiz_siparis_karismaz(self):
        self.sevkiyat(self.diger, D(2026, 9, 10))
        t = SevkiyatTalep.objects.create(sube=self.merkez, durum='Talep')       # henüz onaylanmamış
        SevkiyatKalem.objects.create(talep=t, urun_ad=self.urun.ad, form='TEMIZLIK', koli_icerigi=20,
                                     istenen_miktar=5, istenen_birim='KOLİ')
        self.kaydet(self.sef, 'ilk', '2026-08-31', '3')
        v = tz.veri_hesapla([self.merkez], AY, bugun=D(2026, 9, 20))
        self.assertTrue(all(r['ilave'] == 0 for r in v['toplam']))

    def test_duzeltme_ilaveye_eklenir_ve_silinir(self):
        self.sevkiyat(self.merkez, D(2026, 9, 5))
        self.kaydet(self.sef, 'ilk', '2026-08-31', '10')
        self.kaydet(self.sef, 'son', '2026-09-28', '5')
        self.client.post(reverse('temizlik_giris'), {'islem': 'duzeltme_ekle', 'ay': '2026-09', 'urun': self.urun.id,
                                                      'tarih': '2026-09-12', 'miktar': '-3', 'aciklama': 'iade'})
        _, r = self.hesap()
        self.assertEqual(r['duzeltme'], Decimal('-3'))
        self.assertEqual(r['kullanim'], Decimal('22'))   # 10 + 20 - 3 - 5
        d = TemizlikDuzeltme.objects.get()
        self.client.post(reverse('temizlik_giris'), {'islem': 'duzeltme_sil', 'ay': '2026-09', 'id': d.id})
        self.assertEqual(TemizlikDuzeltme.objects.count(), 0)

    def test_donem_disi_duzeltme_reddedilir(self):
        self.kaydet(self.sef, 'ilk', '2026-08-31', '10')
        self.client.post(reverse('temizlik_giris'), {'islem': 'duzeltme_ekle', 'ay': '2026-09', 'urun': self.urun.id,
                                                      'tarih': '2026-08-20', 'miktar': '4'})
        self.assertEqual(TemizlikDuzeltme.objects.count(), 0)

    def test_eksik_sayim_kullanim_hesaplanmaz(self):
        self.kaydet(self.sef, 'ilk', '2026-08-31', '10')
        _, r = self.hesap()
        self.assertIsNone(r['kullanim'])

    def test_hafta_ve_gun_tahmini_toplami_kullanima_esit(self):
        self.sevkiyat(self.merkez, D(2026, 9, 6))
        self.kaydet(self.sef, 'ilk', '2026-08-31', '50')
        self.kaydet(self.sef, 'son', '2026-09-28', '10')
        v, r = self.hesap()
        for gorunum in ('haftalik', 'gunluk'):
            parcalar = tz.takvim_parcalari(AY, gorunum)
            toplam = sum(tz.parca_toplam(r['gun_tuketim'], p) for p in parcalar)
            self.assertAlmostEqual(float(toplam), float(r['kullanim']), places=4)
        ilave = sum(tz.parca_toplam(r['gun_ilave'], p) for p in tz.takvim_parcalari(AY, 'haftalik'))
        self.assertEqual(ilave, Decimal('20'))

    # ---- doğrulama
    def test_gecersiz_girisler(self):
        for tarih, deger in (('2026-08-31', 'abc'), ('2026-08-31', '-4'), ('2026-07-01', '5'), ('', '5')):
            self.kaydet(self.sef, 'ilk', tarih, deger)
        self.assertEqual(TemizlikSayim.objects.count(), 0)
        self.kaydet(self.sef, 'ilk', '2026-08-31', '5')
        self.kaydet(self.sef, 'son', '2026-08-30', '5')          # ilk sayımdan önce
        self.assertFalse(TemizlikSayim.objects.filter(tur='SON').exists())
        self.kaydet(self.sef, 'ilk', '2026-08-31', '7,5')        # virgüllü sayı geçerli, üzerine yazar
        self.assertEqual(TemizlikSayim.objects.get(tur='ILK').kalemler.get().miktar, Decimal('7.50'))
        self.assertEqual(TemizlikSayim.objects.count(), 1)

    # ---- yetki
    def test_sef_baska_subeye_yazamaz(self):
        self.kaydet(self.sef, 'ilk', '2026-08-31', '9', sube=self.diger)    # şef kendi şubesine düşer
        sy = TemizlikSayim.objects.get()
        self.assertEqual(sy.sube_id, self.merkez.id)

    def test_gm_istedigi_subeye_yazar(self):
        self.kaydet(self.gm, 'ilk', '2026-08-31', '9', sube=self.diger)
        self.assertEqual(TemizlikSayim.objects.get().sube_id, self.diger.id)

    def test_roller(self):
        self.client.force_login(self.pers.user)
        self.assertEqual(self.client.get(reverse('temizlik_giris')).status_code, 302)
        self.assertEqual(self.client.get(reverse('temizlik_rapor')).status_code, 302)
        self.client.force_login(self.sa.user)
        self.assertEqual(self.client.get(reverse('temizlik_rapor')).status_code, 200)
        r = self.client.post(reverse('temizlik_sayim', args=['ilk']), {
            'ay': '2026-09', 'tarih': '2026-08-31', 'sube': self.merkez.id, 'adet_%d' % self.urun.id: '5'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(TemizlikSayim.objects.count(), 0)          # satın alma sayım giremez
        self.assertEqual(self.client.get(reverse('temizlik_sayim', args=['ilk'])).status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('temizlik_rapor')).status_code, 302)

    def test_sef_raporda_yalniz_kendi_subesi(self):
        self.client.force_login(self.sef.user)
        r = self.client.get(reverse('temizlik_rapor'))
        self.assertEqual([c['sube'].id for c in r.context['veri']['subeler']], [self.merkez.id])
        r = self.client.get(reverse('temizlik_rapor') + '?sube=%d' % self.diger.id)
        self.assertEqual([c['sube'].id for c in r.context['veri']['subeler']], [self.merkez.id])

    def test_bolge_muduru_sorumlu_subeleri_gorur(self):
        mudur = kisi(Rol.MUDUR, None, 'Bölge')
        mudur.sorumlu_subeler.add(self.diger)
        self.client.force_login(mudur.user)
        r = self.client.get(reverse('temizlik_rapor'))
        self.assertEqual([c['sube'].id for c in r.context['veri']['subeler']], [self.diger.id])

    # ---- rapor çıktıları
    def test_excel_ve_pdf(self):
        import openpyxl
        self.sevkiyat(self.merkez, D(2026, 9, 5))
        self.kaydet(self.sef, 'ilk', '2026-08-31', '10')
        self.kaydet(self.sef, 'son', '2026-09-28', '4')
        self.client.force_login(self.gm.user)
        beklenen = {'aylik': 'Şube Kırılımı', 'haftalik': 'Haftalık İlave', 'gunluk': 'Günlük İlave'}
        for gorunum, sayfa in beklenen.items():
            q = '?ay=2026-09&gorunum=%s&bicim=' % gorunum
            x = self.client.get(reverse('temizlik_rapor_indir') + q + 'xlsx')
            self.assertEqual(x.status_code, 200)
            wb = openpyxl.load_workbook(io.BytesIO(x.content))
            self.assertIn(sayfa, wb.sheetnames)
            satir = [c.value for c in next(wb['Aylık Özet'].iter_rows(min_row=6, max_row=6))]
            self.assertEqual((satir[0], satir[6]), ('CAM SİL 500 ML', 26))          # 10 + 20 - 4
            p = self.client.get(reverse('temizlik_rapor_indir') + q + 'pdf')
            self.assertEqual(p.status_code, 200)
            self.assertTrue(p.content.startswith(b'%PDF'))

    def test_sayfalar_aciliyor(self):
        self.sevkiyat(self.merkez, D(2026, 9, 5))
        for kisi_ in (self.sef, self.gm, self.sa):
            self.client.force_login(kisi_.user)
            for g in ('aylik', 'haftalik', 'gunluk'):
                self.assertEqual(self.client.get(reverse('temizlik_rapor') + '?ay=2026-09&gorunum=' + g).status_code, 200)
            self.assertEqual(self.client.get(reverse('temizlik_rapor') + '?ay=zzz&gorunum=x&sube=abc').status_code, 200)
        self.client.force_login(self.sef.user)
        r = self.client.get(reverse('temizlik_giris') + '?ay=2026-09')
        self.assertContains(r, 'Temizlik Tüketimi')
        self.assertContains(r, 'CAM SİL 500 ML')
        self.assertEqual(self.client.get(reverse('temizlik')).status_code, 302)

    def test_menude_baglanti(self):
        for kisi_ in (self.sef, self.gm, self.sa):
            self.client.force_login(kisi_.user)
            self.assertContains(self.client.get(reverse('temizlik_rapor')), reverse('temizlik'))


@override_settings(**_AYAR)
class TemizlikUrunVeSayimTestleri(TestCase):
    def setUp(self):
        self.merkez = Sube.objects.create(ad='Merkez')
        self.sef = kisi(Rol.SEF, self.merkez, 'Şef')
        self.gm = kisi(Rol.GENEL_MUDUR, None, 'GM')
        self.sa = kisi(Rol.SATIN_ALMA, None, 'SA')
        self.cam = TemizlikUrun.objects.get(ad='CAM SİL 500 ML')        # koli 20, kapasite 500 ml
        self.mop = TemizlikUrun.objects.get(ad='MOP BEZİ')              # kapasitesiz

    def sayim(self, kisi_, tur, tarih, **alanlar):
        self.client.force_login(kisi_.user)
        veri = {'ay': '2026-09', 'tarih': tarih}
        veri.update(alanlar)
        return self.client.post(reverse('temizlik_sayim', args=[tur]), veri)

    # ---- kapalı + açık
    def test_koli_adet_ve_acik_kap_toplami(self):
        self.sayim(self.sef, 'ilk', '2026-08-31', **{'koli_%d' % self.cam.id: '1', 'adet_%d' % self.cam.id: '10',
                                                     'acik_%d' % self.cam.id: '300'})
        k = TemizlikSayim.objects.get().kalemler.get()
        self.assertEqual(k.miktar, Decimal('30.60'))                    # 1×20 + 10 + 300/500
        self.assertEqual((k.koli, k.adet, k.acik), (Decimal('1'), Decimal('10'), Decimal('300')))

    def test_kullanim_hacim_karsiligi(self):
        self.assertEqual(tz.toplam_adet(self.cam, None, Decimal('10'), Decimal('300')), Decimal('10.60'))
        self.assertEqual(tz.hacim_karsiligi(Decimal('12.4'), self.cam), '≈ 6.200 ml')
        self.assertEqual(tz.hacim_karsiligi(Decimal('3'), self.mop), '')

    def test_kapasitesiz_urunde_acik_deger_yok_sayilir(self):
        self.sayim(self.sef, 'ilk', '2026-08-31', **{'adet_%d' % self.mop.id: '4', 'acik_%d' % self.mop.id: '999'})
        self.assertEqual(TemizlikSayim.objects.get().kalemler.get().miktar, Decimal('4.00'))

    def test_sayim_sayfasi_ve_onceki_degerler(self):
        self.sayim(self.sef, 'ilk', '2026-08-31', **{'adet_%d' % self.cam.id: '10', 'acik_%d' % self.cam.id: '300'})
        r = self.client.get(reverse('temizlik_sayim', args=['ilk']) + '?ay=2026-09')
        self.assertContains(r, 'İlk stok sayımı')
        self.assertContains(r, 'value="300"')
        self.assertContains(r, 'Açık kapta kalan')
        self.assertEqual(self.client.get(reverse('temizlik_sayim', args=['x'])).status_code, 302)

    def test_hatali_sayim_girdileri_kayit_olusturmaz(self):
        for alanlar in ({'adet_%d' % self.cam.id: 'abc'}, {'koli_%d' % self.cam.id: '-1'}, {}):
            self.sayim(self.sef, 'ilk', '2026-08-31', **alanlar)
        self.assertEqual(TemizlikSayim.objects.count(), 0)

    def test_koli_icerigi_degisse_eski_sayim_bozulmaz(self):
        self.sayim(self.sef, 'ilk', '2026-08-31', **{'koli_%d' % self.cam.id: '2'})      # 2 × 20 = 40
        self.cam.koli_icerigi = 24
        self.cam.save()
        self.assertEqual(TemizlikSayim.objects.get().kalemler.get().miktar, Decimal('40.00'))

    # ---- ürün düzenleme
    def urun_post(self, kisi_, **alanlar):
        self.client.force_login(kisi_.user)
        return self.client.post(reverse('temizlik_urunler'), alanlar)

    def test_urun_ekle_duzenle(self):
        self.urun_post(self.gm, islem='ekle', ad='  Yeni   Sprey ', birim='ADET', koli_icerigi='12', hacim='750',
                       hacim_birim='ML')
        u = TemizlikUrun.objects.get(ad='Yeni Sprey')
        self.assertEqual((u.koli_icerigi, u.hacim, u.hacim_birim, u.aktif), (Decimal('12'), Decimal('750'), 'ML', True))
        self.assertGreater(u.sira, 43)
        self.urun_post(self.sa, islem='kaydet', id=u.id, ad='Yeni Sprey 1 LT', birim='PAKET', koli_icerigi='6',
                       hacim='', hacim_birim='ML', sira='5')
        u.refresh_from_db()
        self.assertEqual((u.ad, u.birim, u.hacim, u.hacim_birim, u.sira), ('Yeni Sprey 1 LT', 'PAKET', None, '', 5))

    def test_urun_dogrulama(self):
        sayi = TemizlikUrun.objects.count()
        for alanlar in (dict(ad=''), dict(ad='cam sil 500 ml'), dict(ad='X', birim='LITRE'), dict(ad='X', koli_icerigi='0'),
                        dict(ad='X', koli_icerigi='abc'), dict(ad='X', hacim='500', hacim_birim=''),
                        dict(ad='X', hacim='-5', hacim_birim='ML')):
            self.urun_post(self.gm, islem='ekle', **dict(dict(birim='ADET', koli_icerigi='1'), **alanlar))
        self.assertEqual(TemizlikUrun.objects.count(), sayi)

    def test_kullanilmis_urun_pasiflesir_kullanilmamis_silinir(self):
        self.sayim(self.sef, 'ilk', '2026-08-31', **{'adet_%d' % self.cam.id: '3'})
        self.urun_post(self.gm, islem='cikar', id=self.cam.id)
        self.cam.refresh_from_db()
        self.assertFalse(self.cam.aktif)                                   # geçmiş sayım var -> silinmedi
        self.assertEqual(TemizlikSayim.objects.get().kalemler.count(), 1)
        self.urun_post(self.gm, islem='cikar', id=self.mop.id)             # hiç kullanılmadı -> silinir
        self.assertFalse(TemizlikUrun.objects.filter(id=self.mop.id).exists())
        self.urun_post(self.gm, islem='geri_al', id=self.cam.id)
        self.cam.refresh_from_db()
        self.assertTrue(self.cam.aktif)

    def test_pasif_urun_sayim_listesinde_yok_ama_gecmis_raporda_var(self):
        self.sayim(self.sef, 'ilk', '2026-08-31', **{'adet_%d' % self.cam.id: '3'})
        self.urun_post(self.gm, islem='cikar', id=self.cam.id)
        self.client.force_login(self.sef.user)
        self.assertNotContains(self.client.get(reverse('temizlik_sayim', args=['son']) + '?ay=2026-09'), 'name="adet_%d"' % self.cam.id)
        v = tz.veri_hesapla([self.merkez], AY, bugun=D(2026, 9, 20))
        self.assertTrue(any(r['urun'].id == self.cam.id and r['ilk'] == Decimal('3') for r in v['toplam']))

    def test_urun_duzenleme_yetkisi(self):
        self.client.force_login(self.sef.user)
        self.assertEqual(self.client.get(reverse('temizlik_urunler')).status_code, 302)
        sayi = TemizlikUrun.objects.count()
        self.urun_post(self.sef, islem='ekle', ad='Yetkisiz', birim='ADET', koli_icerigi='1')
        self.assertEqual(TemizlikUrun.objects.count(), sayi)
        for k in (self.gm, self.sa):
            self.client.force_login(k.user)
            r = self.client.get(reverse('temizlik_urunler'))
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, 'Yeni ürün ekle')

    def test_giris_sayfasinda_urun_duzenle_baglantisi(self):
        self.client.force_login(self.gm.user)
        self.assertContains(self.client.get(reverse('temizlik_giris')), reverse('temizlik_urunler'))
        self.client.force_login(self.sef.user)
        self.assertNotContains(self.client.get(reverse('temizlik_giris')), reverse('temizlik_urunler'))
