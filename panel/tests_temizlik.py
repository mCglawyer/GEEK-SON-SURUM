"""Temizlik malzemesi tüketimi:  python manage.py test panel.tests_temizlik"""
import datetime
import io
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import temizlik as tz
from .models import (Rol, SevkiyatKalem, SevkiyatTalep, Sube, TemizlikAyar, TemizlikDuzeltme, TemizlikFiyat,
                     TemizlikSayim, TemizlikUrun)
from .tests_mola_stok import _AYAR, kisi

AY = datetime.date(2026, 9, 1)
D = datetime.date


def _zaman(gun):
    return timezone.make_aware(datetime.datetime.combine(gun, datetime.time(12, 0)))


@override_settings(**_AYAR)
class TemizlikTestleri(TestCase):
    def setUp(self):
        TemizlikAyar.objects.all().delete()
        TemizlikAyar.objects.create(aktif=True, baslangic=None)
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
        TemizlikAyar.objects.all().delete()
        TemizlikAyar.objects.create(aktif=True, baslangic=None)
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


@override_settings(**_AYAR)
class TemizlikSistemVeFiyatTestleri(TestCase):
    """Aç/kapa, başlangıç tarihi, sıfırlama, fiyat yetkisi ve tutar hesabı."""

    def setUp(self):
        TemizlikAyar.objects.all().delete()
        self.ayar = TemizlikAyar.objects.create(aktif=True, baslangic=None)
        self.merkez = Sube.objects.create(ad='Merkez')
        self.sef = kisi(Rol.SEF, self.merkez, 'Şef')
        self.mm = kisi(Rol.MAGAZA_MUDURU, self.merkez, 'MM')
        self.gm = kisi(Rol.GENEL_MUDUR, None, 'GM')
        self.op = kisi(Rol.OPERATOR, None, 'Op')
        self.sa = kisi(Rol.SATIN_ALMA, None, 'SA')
        self.yat = kisi(Rol.YATIRIMCI, None, 'Yat')
        self.mud = kisi(Rol.MUDUR, None, 'Bölge')
        self.mud.sorumlu_subeler.add(self.merkez)
        self.cam = TemizlikUrun.objects.get(ad='CAM SİL 500 ML')      # 500 ml / adet, koli 20
        self.erna = TemizlikUrun.objects.filter(hacim_birim='KG').first()   # kg kapasiteli
        self.mop = TemizlikUrun.objects.get(ad='MOP BEZİ')            # kapasitesiz

    def get(self, kisi_, ad, **q):
        self.client.force_login(kisi_.user)
        return self.client.get(reverse(ad), q)

    def post(self, kisi_, ad, **veri):
        self.client.force_login(kisi_.user)
        return self.client.post(reverse(ad), veri)

    def tam_sayim(self, ilk=10, son=4, urun=None):
        """Merkez şubesinde Eylül dönemi: ilk 10, son 4, sevkiyat yok -> kullanım 6."""
        urun = urun or self.cam
        for tur, gun, d in (('ILK', D(2026, 9, 1), ilk), ('SON', D(2026, 9, 30), son)):
            sy = TemizlikSayim.objects.create(sube=self.merkez, ay=AY, tur=tur, tarih=gun)
            sy.kalemler.create(urun=urun, urun_ad=urun.ad, miktar=Decimal(d), adet=Decimal(d))

    # ---- aç / kapa
    def test_kapaliyken_sef_ve_muduru_goremez_yonetim_gorur(self):
        self.ayar.aktif = False
        self.ayar.save()
        for k in (self.sef, self.mm, self.mud, self.yat):
            for ad in ('temizlik_giris', 'temizlik_rapor', 'temizlik_fiyatlar'):
                r = self.get(k, ad)
                self.assertEqual(r.status_code, 200, (k, ad))
                self.assertContains(r, 'şu an kapalı')
        for k in (self.gm, self.op, self.sa):
            self.assertEqual(self.get(k, 'temizlik_rapor').status_code, 200)
            self.assertNotContains(self.get(k, 'temizlik_rapor'), 'şu an kapalı')

    def test_menu_baglantisi_kapaliyken_gizlenir(self):
        self.ayar.aktif = False
        self.ayar.save()
        self.assertNotContains(self.get(self.sef, 'sevkiyat'), 'href="/temizlik/"')
        self.assertContains(self.get(self.gm, 'sevkiyat'), 'href="/temizlik/"')
        self.ayar.aktif = True
        self.ayar.save()
        self.assertContains(self.get(self.sef, 'sevkiyat'), 'href="/temizlik/"')

    def test_ac_kapa_yalniz_gm_ve_operator(self):
        self.post(self.gm, 'temizlik_ayarlar', islem='kapat')
        self.ayar.refresh_from_db()
        self.assertFalse(self.ayar.aktif)
        self.post(self.op, 'temizlik_ayarlar', islem='ac')
        self.ayar.refresh_from_db()
        self.assertTrue(self.ayar.aktif)
        for k in (self.sef, self.mm, self.sa, self.yat, self.mud):
            r = self.post(k, 'temizlik_ayarlar', islem='kapat')
            self.assertEqual(r.status_code, 302)
            self.ayar.refresh_from_db()
            self.assertTrue(self.ayar.aktif, k)

    def test_varsayilan_ayar_kapali_ve_gelecek_ay(self):
        TemizlikAyar.objects.all().delete()
        a = TemizlikAyar.al()
        self.assertFalse(a.aktif)
        self.assertEqual(a.baslangic.day, 1)
        self.assertGreater(a.baslangic, datetime.date.today())

    # ---- başlangıç tarihi
    def test_baslangictan_onceki_sevkiyat_sayilmaz(self):
        self.tam_sayim()
        t = SevkiyatTalep.objects.create(sube=self.merkez, durum='Teslim Edildi')
        SevkiyatTalep.objects.filter(pk=t.pk).update(onay_tarih=_zaman(D(2026, 9, 5)))
        SevkiyatKalem.objects.create(talep=t, urun=None, urun_ad=self.cam.ad, form='TEMIZLIK', koli_icerigi=20,
                                     istenen_miktar=1, istenen_birim='KOLİ', sevkiyat_miktar=1, sevkiyat_birim='KOLİ')

        def ilave():
            v = tz.veri_hesapla([self.merkez], AY, bugun=D(2026, 10, 5))
            return next(r for r in v['toplam'] if r['urun'].id == self.cam.id)['ilave']
        self.assertEqual(ilave(), Decimal('20'))
        self.ayar.baslangic = D(2026, 9, 10)
        self.ayar.save()
        self.assertEqual(ilave(), Decimal('0'))

    def test_baslangic_ayindan_onceki_aya_sayim_girilemez(self):
        self.ayar.baslangic = D(2026, 11, 1)
        self.ayar.save()
        self.client.force_login(self.sef.user)
        r = self.client.post(reverse('temizlik_sayim', args=['ilk']), {
            'ay': '2026-09', 'tarih': '2026-09-01', 'adet_%d' % self.cam.id: '5'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(TemizlikSayim.objects.exists())
        r = self.client.post(reverse('temizlik_sayim', args=['ilk']), {
            'ay': '2026-11', 'tarih': '2026-10-31', 'adet_%d' % self.cam.id: '5'})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(TemizlikSayim.objects.filter(ay=D(2026, 11, 1), tur='ILK', tarih=D(2026, 10, 31)).exists())

    def test_baslangic_kaydet_ve_kaldir(self):
        self.post(self.gm, 'temizlik_ayarlar', islem='baslangic', baslangic='2026-11-01')
        self.ayar.refresh_from_db()
        self.assertEqual(self.ayar.baslangic, D(2026, 11, 1))
        self.post(self.gm, 'temizlik_ayarlar', islem='baslangic', baslangic='bozuk')
        self.ayar.refresh_from_db()
        self.assertEqual(self.ayar.baslangic, D(2026, 11, 1))
        self.post(self.gm, 'temizlik_ayarlar', islem='baslangic', baslangic='')
        self.ayar.refresh_from_db()
        self.assertIsNone(self.ayar.baslangic)

    # ---- sıfırlama
    def test_sifirla_onay_ister_ve_sevkiyata_dokunmaz(self):
        self.tam_sayim()
        TemizlikDuzeltme.objects.create(sube=self.merkez, ay=AY, urun=self.cam, urun_ad=self.cam.ad, tarih=D(2026, 9, 5),
                                        miktar=Decimal('2'))
        t = SevkiyatTalep.objects.create(sube=self.merkez, durum='Teslim Edildi')
        self.post(self.gm, 'temizlik_ayarlar', islem='sifirla', sube='', onay='yanlis')
        self.assertEqual(TemizlikSayim.objects.count(), 2)
        self.post(self.gm, 'temizlik_ayarlar', islem='sifirla', sube='', onay=' sifirla ')
        self.assertEqual(TemizlikSayim.objects.count(), 0)
        self.assertEqual(TemizlikDuzeltme.objects.count(), 0)
        self.assertTrue(SevkiyatTalep.objects.filter(pk=t.pk).exists())
        self.assertTrue(TemizlikUrun.objects.exists())
        self.ayar.refresh_from_db()
        self.assertIsNotNone(self.ayar.son_sifirlama)

    def test_sifirla_tek_sube_ve_yetki(self):
        diger = Sube.objects.create(ad='Diğer')
        self.tam_sayim()
        for tur, gun in (('ILK', D(2026, 9, 1)), ('SON', D(2026, 9, 30))):
            TemizlikSayim.objects.create(sube=diger, ay=AY, tur=tur, tarih=gun)
        for k in (self.sef, self.sa, self.yat):
            self.post(k, 'temizlik_ayarlar', islem='sifirla', sube='', onay='SIFIRLA')
        self.assertEqual(TemizlikSayim.objects.count(), 4)
        self.post(self.op, 'temizlik_ayarlar', islem='sifirla', sube=diger.id, onay='SIFIRLA')
        self.assertEqual(set(TemizlikSayim.objects.values_list('sube__ad', flat=True)), {'Merkez'})

    # ---- fiyat yetkisi
    def test_fiyat_sayfasi_yetkileri(self):
        for k in (self.sa, self.gm, self.op, self.yat, self.mud):
            self.assertEqual(self.get(k, 'temizlik_fiyatlar').status_code, 200, k)
        for k in (self.sef, self.mm):
            r = self.get(k, 'temizlik_fiyatlar')
            self.assertEqual(r.status_code, 302, k)
        self.assertContains(self.get(self.sa, 'temizlik_fiyatlar'), 'name="fiyat_%d"' % self.cam.id)
        self.assertNotContains(self.get(self.op, 'temizlik_fiyatlar'), 'name="fiyat_%d"' % self.cam.id)
        self.assertNotContains(self.get(self.yat, 'temizlik_fiyatlar'), 'name="fiyat_%d"' % self.cam.id)

    def test_fiyati_yalniz_satin_alma_ve_gm_yazar(self):
        for k in (self.op, self.yat, self.mud, self.sef, self.mm):
            self.post(k, 'temizlik_fiyatlar', **{'fiyat_%d' % self.cam.id: '10', 'birim_%d' % self.cam.id: 'ADET'})
        self.assertFalse(TemizlikFiyat.objects.exists())
        self.post(self.sa, 'temizlik_fiyatlar', **{'fiyat_%d' % self.cam.id: '12,50', 'birim_%d' % self.cam.id: 'ADET'})
        self.assertEqual(TemizlikFiyat.objects.get(urun=self.cam).fiyat, Decimal('12.50'))
        self.post(self.gm, 'temizlik_fiyatlar', **{'fiyat_%d' % self.cam.id: '14', 'birim_%d' % self.cam.id: 'ADET'})
        self.assertEqual(TemizlikFiyat.objects.get(urun=self.cam).fiyat, Decimal('14.00'))      # aynı gün: güncellenir
        self.assertEqual(TemizlikFiyat.objects.count(), 1)

    def test_fiyat_dogrulama(self):
        kg = self.erna
        for veri in ({'fiyat_%d' % self.cam.id: 'abc', 'birim_%d' % self.cam.id: 'ADET'},
                     {'fiyat_%d' % self.cam.id: '-5', 'birim_%d' % self.cam.id: 'ADET'},
                     {'fiyat_%d' % self.cam.id: '0', 'birim_%d' % self.cam.id: 'ADET'},
                     {'fiyat_%d' % self.cam.id: '10', 'birim_%d' % self.cam.id: 'KG'},      # ml kapasiteli ürüne kg fiyatı
                     {'fiyat_%d' % self.mop.id: '10', 'birim_%d' % self.mop.id: 'LT'},      # kapasitesiz ürüne litre fiyatı
                     {'fiyat_%d' % kg.id: '10', 'birim_%d' % kg.id: 'LT'}):
            self.post(self.sa, 'temizlik_fiyatlar', **veri)
        self.assertFalse(TemizlikFiyat.objects.exists())
        # hatalı satır varsa geçerli satır da kaydedilmez
        self.post(self.sa, 'temizlik_fiyatlar', **{'fiyat_%d' % self.cam.id: '10', 'birim_%d' % self.cam.id: 'ADET',
                                                    'fiyat_%d' % self.mop.id: 'x', 'birim_%d' % self.mop.id: 'ADET'})
        self.assertFalse(TemizlikFiyat.objects.exists())

    def test_birim_donusumu(self):
        self.assertEqual(tz.adet_fiyati(self.cam, Decimal('40'), 'LT'), Decimal('20'))       # 500 ml = 0,5 lt
        self.assertEqual(tz.adet_fiyati(self.cam, Decimal('7'), 'ADET'), Decimal('7'))
        self.assertIsNone(tz.adet_fiyati(self.cam, Decimal('40'), 'KG'))
        self.assertIsNone(tz.adet_fiyati(self.mop, Decimal('40'), 'LT'))
        self.assertEqual(tz.adet_fiyati(self.erna, Decimal('100'), 'KG'), Decimal('500'))     # 5 kg
        self.assertEqual(tz.para_yaz(Decimal('1250.5')), '1.250,50')

    def test_fiyat_gecmisi_aylara_gore(self):
        f1 = TemizlikFiyat.objects.create(urun=self.cam, fiyat=Decimal('10'), birim='ADET', gecerli=D(2026, 8, 20))
        TemizlikFiyat.objects.create(urun=self.cam, fiyat=Decimal('12'), birim='ADET', gecerli=D(2026, 10, 3))
        self.assertEqual(tz.fiyat_haritasi(D(2026, 9, 1))[self.cam.id]['fiyat'], Decimal('10'))
        self.assertEqual(tz.fiyat_haritasi(D(2026, 10, 1))[self.cam.id]['fiyat'], Decimal('12'))
        self.assertEqual(tz.fiyat_haritasi(D(2026, 7, 1))[self.cam.id]['fiyat'], Decimal('10'))   # öncesi: en eski
        self.assertEqual(tz.fiyat_haritasi(None)[self.cam.id]['fiyat'], Decimal('12'))
        self.assertTrue(f1.pk)

    # ---- tutar
    def test_tutar_hesabi_ve_eksik_fiyat(self):
        self.tam_sayim(ilk=10, son=4)                                    # kullanım 6 adet
        TemizlikFiyat.objects.create(urun=self.cam, fiyat=Decimal('40'), birim='LT', gecerli=D(2026, 8, 1))
        v = tz.veri_hesapla([self.merkez], AY, bugun=D(2026, 10, 5), fiyatli=True)
        r = next(x for x in v['toplam'] if x['urun'].id == self.cam.id)
        self.assertEqual(r['kullanim'], Decimal('6'))
        self.assertEqual(r['tutar'], Decimal('120.0000'))                # 6 × 20 TL
        self.assertEqual(v['genel_tutar'], Decimal('120'))
        self.assertEqual(v['subeler'][0]['tutar'], Decimal('120'))
        self.assertEqual(v['fiyat_eksik'], [])
        # fiyatsız ürün kullanımı -> uyarı, toplama girmez
        for sy in TemizlikSayim.objects.all():
            sy.kalemler.create(urun=self.mop, urun_ad=self.mop.ad, miktar=Decimal('5' if sy.tur == 'ILK' else '2'))
        v = tz.veri_hesapla([self.merkez], AY, bugun=D(2026, 10, 5), fiyatli=True)
        self.assertEqual(v['fiyat_eksik'], [self.mop.ad])
        self.assertEqual(v['genel_tutar'], Decimal('120'))
        # fiyatsız istek -> alanlar hiç yok
        v = tz.veri_hesapla([self.merkez], AY, bugun=D(2026, 10, 5))
        self.assertNotIn('genel_tutar', v)
        self.assertNotIn('tutar', v['toplam'][0])

    def test_rapor_tutari_yalniz_yetkili_roller_gorur(self):
        self.tam_sayim()
        TemizlikFiyat.objects.create(urun=self.cam, fiyat=Decimal('40'), birim='LT', gecerli=D(2026, 8, 1))
        q = {'ay': '2026-09', 'sube': self.merkez.id}
        for k in (self.sa, self.yat, self.mud, self.op, self.gm):
            r = self.get(k, 'temizlik_rapor', **q)
            self.assertContains(r, 'Toplam tutar', msg_prefix=str(k))
            self.assertContains(r, '120,00 ₺')
        for k in (self.sef, self.mm):
            r = self.get(k, 'temizlik_rapor', **q)
            self.assertNotContains(r, 'Toplam tutar')
            self.assertNotContains(r, '120,00')
            self.assertNotContains(r, 'Birim fiyat')

    def test_excel_ve_pdf_tutar_sutunlari(self):
        import openpyxl
        self.tam_sayim()
        TemizlikFiyat.objects.create(urun=self.cam, fiyat=Decimal('40'), birim='LT', gecerli=D(2026, 8, 1))
        q = {'ay': '2026-09', 'sube': self.merkez.id, 'bicim': 'xlsx'}
        r = self.get(self.sa, 'temizlik_rapor_indir', **q)
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        self.assertIn('Şube Tutarı', wb.sheetnames)
        ws = wb['Aylık Özet']
        basliklar = [c.value for c in ws[5]]
        self.assertIn('Tutar (TL)', basliklar)
        self.assertTrue(any(c.value == 120 for row in ws.iter_rows(min_row=6) for c in row))
        r = self.get(self.sef, 'temizlik_rapor_indir', **q)
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        self.assertNotIn('Şube Tutarı', wb.sheetnames)
        self.assertNotIn('Tutar (TL)', [c.value for c in wb['Aylık Özet'][5]])
        q['bicim'] = 'pdf'
        for k in (self.sa, self.sef):
            self.assertTrue(self.get(k, 'temizlik_rapor_indir', **q).content.startswith(b'%PDF'))

    def test_varsayilan_ay_sistem_baslamadiysa_baslangic_ayi(self):
        self.ayar.baslangic = datetime.date.today().replace(day=1) + datetime.timedelta(days=40)
        self.ayar.baslangic = self.ayar.baslangic.replace(day=1)
        self.ayar.save()
        self.assertEqual(tz.varsayilan_ay(self.ayar), self.ayar.baslangic)
        self.ayar.baslangic = None
        self.assertEqual(tz.varsayilan_ay(self.ayar), tz.ay_oku(None))

    def test_sayfalar_aciliyor(self):
        for k, ad in ((self.gm, 'temizlik_ayarlar'), (self.op, 'temizlik_ayarlar'), (self.sa, 'temizlik_fiyatlar'),
                      (self.gm, 'temizlik_giris'), (self.gm, 'temizlik_rapor'), (self.sa, 'temizlik_urunler')):
            self.assertEqual(self.get(k, ad).status_code, 200, (k, ad))
        for k in (self.sef, self.sa, self.yat, self.mud, self.mm):
            self.assertEqual(self.get(k, 'temizlik_ayarlar').status_code, 302)
