"""Temizlik -> Tüketim & Maliyet birleşimi:  python manage.py test panel.tests_temizlik_tasima"""
import datetime
import importlib
from decimal import Decimal

from django.apps import apps
from django.test import TestCase, override_settings
from django.urls import reverse

from . import tuketim as tk
from .models import (Rol, SevkiyatKalem, SevkiyatTalep, StokSayim, StokSayimKalem, StokUrun, Sube, TemizlikFiyat,
                     TemizlikSayim, TemizlikSayimKalem, TemizlikUrun, TuketimAyar, TuketimFiyat, Urun)
from .tests_mola_stok import _AYAR, kisi

D = datetime.date


@override_settings(**_AYAR)
class TemizlikTasimaTesti(TestCase):
    def setUp(self):
        TuketimAyar.objects.all().delete()
        self.ayar = TuketimAyar.objects.create(aktif=True, baslangic=None, son_gun_ayda=True)
        self.sube = Sube.objects.create(ad='Tasima Şube')
        self.sevk = Urun.objects.create(form='TEMIZLIK', kategori='TEMİZLİK MALZEMESİ', ad='CAM SİL 500 ML',
                                        koli_icerigi=20, birim='ADET', ust_birim='KOLİ')
        self.tu = TemizlikUrun.objects.create(ad='Cam sil 500 ml', birim='ADET', koli_icerigi=20, hacim=Decimal('500'),
                                              hacim_birim='ML', urun=self.sevk)

    def sayim(self, ay, tur, miktar, tarih):
        sy = TemizlikSayim.objects.create(sube=self.sube, ay=ay, tur=tur, tarih=tarih)
        TemizlikSayimKalem.objects.create(sayim=sy, urun=self.tu, urun_ad=self.tu.ad, miktar=Decimal(miktar))

    def bar_sayim(self, ay):
        return StokSayim.objects.create(sube=self.sube, ay=ay)

    def calistir(self):
        m = importlib.import_module('panel.migrations.0074_temizlik_tuketime_tasi')
        m.ileri(apps, None)

    def test_urun_sayim_ve_fiyat_tasinir(self):
        self.sayim(D(2026, 9, 1), 'SON', '10', D(2026, 9, 30))        # 10 adet = 5.000 ml
        self.sayim(D(2026, 10, 1), 'SON', '4', D(2026, 10, 31))
        self.bar_sayim(D(2026, 9, 1)); self.bar_sayim(D(2026, 10, 1))
        TemizlikFiyat.objects.create(urun=self.tu, fiyat=Decimal('30'), birim='ADET', gecerli=D(2026, 1, 1))
        TemizlikFiyat.objects.create(urun=self.tu, fiyat=Decimal('60'), birim='LT', gecerli=D(2026, 6, 1))   # 500 ml -> 30
        self.calistir()
        su = StokUrun.objects.get(sevkiyat_urun=self.sevk)
        self.assertEqual((su.kategori, su.kapali_icerik, su.sevkiyat_carpan), (tk.TEMIZLIK_GRUBU, Decimal('500'), Decimal('500')))
        k = StokSayimKalem.objects.get(sayim__ay=D(2026, 9, 1), urun=su)
        self.assertEqual(k.toplam, Decimal('5000'))
        self.assertEqual(TuketimFiyat.objects.filter(urun=self.sevk, grup='FRANCHISE').count(), 2)
        self.assertEqual(TuketimFiyat.objects.get(urun=self.sevk, grup='MERKEZ', gecerli=D(2026, 6, 1)).fiyat, Decimal('30'))
        # tekrar çalıştırmak çoğaltmaz
        self.calistir()
        self.assertEqual(StokUrun.objects.filter(sevkiyat_urun=self.sevk).count(), 1)
        self.assertEqual(StokSayimKalem.objects.filter(urun=su).count(), 2)

    def test_stok_sayimi_yoksa_bos_sayim_olusturulmaz(self):
        self.sayim(D(2026, 10, 1), 'SON', '4', D(2026, 10, 31))
        self.calistir()
        self.assertFalse(StokSayim.objects.exists())

    def test_rapor_temizlik_kullanimi_ve_grup_filtresi(self):
        self.sayim(D(2026, 9, 1), 'SON', '10', D(2026, 9, 30))
        self.sayim(D(2026, 10, 1), 'SON', '4', D(2026, 10, 31))
        self.bar_sayim(D(2026, 9, 1)); self.bar_sayim(D(2026, 10, 1))
        bar = StokUrun.objects.create(kategori='ŞURUP VE SOS', ad='BAR ŞURUP', kapali_icerik=750)
        TemizlikFiyat.objects.create(urun=self.tu, fiyat=Decimal('30'), birim='ADET', gecerli=D(2026, 1, 1))
        self.calistir()
        t = SevkiyatTalep.objects.create(sube=self.sube, durum='Teslim Edildi')
        from django.utils import timezone
        SevkiyatTalep.objects.filter(pk=t.pk).update(onay_tarih=timezone.make_aware(datetime.datetime(2026, 10, 12, 12)))
        SevkiyatKalem.objects.create(talep=t, urun=self.sevk, urun_ad=self.sevk.ad, form='TEMIZLIK', koli_icerigi=20,
                                     istenen_miktar=1, istenen_birim='KOLİ', sevkiyat_miktar=1, sevkiyat_birim='KOLİ')
        v = tk.hesapla([self.sube], D(2026, 10, 1), fiyatli=True, ayar=self.ayar, grup='temizlik')
        r = v['subeler'][0]['satirlar']
        self.assertEqual(len(r), 1)
        # 10 + 20 gelen − 4 = 26 adet × 30 TL
        self.assertEqual(r[0]['kullanim_taban'], Decimal('26'))
        self.assertEqual(v['genel_tutar'], Decimal('780.00'))
        v2 = tk.hesapla([self.sube], D(2026, 10, 1), fiyatli=True, ayar=self.ayar, grup='bar')
        self.assertTrue(all(x['urun'].id != r[0]['urun'].id for x in v2['subeler'][0]['satirlar']))

    def test_temizlik_ekle_butonu_ve_eski_adres(self):
        p = kisi(Rol.SATIN_ALMA)
        self.client.force_login(p.user)
        r = self.client.post(reverse('tuketim_esleme'), {'islem': 'temizlik_ekle'})
        self.assertEqual(r.status_code, 302)
        su = StokUrun.objects.get(sevkiyat_urun=self.sevk)
        self.assertEqual(su.kategori, tk.TEMIZLIK_GRUBU)
        self.client.post(reverse('tuketim_esleme'), {'islem': 'temizlik_ekle'})
        self.assertEqual(StokUrun.objects.filter(sevkiyat_urun=self.sevk).count(), 1)
        self.assertEqual(self.client.get('/temizlik/').status_code, 302)
        self.assertEqual(self.client.get('/temizlik/rapor/').status_code, 302)
        self.assertEqual(self.client.get(reverse('tuketim_rapor') + '?grup=temizlik').status_code, 200)
