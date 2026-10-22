"""Bar tüketim & maliyet motoru:  python manage.py test panel.tests_tuketim"""
import datetime
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import tuketim as tk
from .models import (Rol, SevkiyatKalem, SevkiyatTalep, StokSayim, StokSayimKalem, StokUrun, Sube, TuketimAyar,
                     TuketimFiyat, Urun)
from .tests_mola_stok import _AYAR, kisi

D = datetime.date
EKIM = D(2026, 10, 1)
EYLUL = D(2026, 9, 1)


def _zaman(gun, saat=12):
    return timezone.make_aware(datetime.datetime.combine(gun, datetime.time(saat, 0)))


@override_settings(**_AYAR)
class TuketimMotoruTesti(TestCase):
    def setUp(self):
        TuketimAyar.objects.all().delete()
        self.ayar = TuketimAyar.objects.create(aktif=True, baslangic=None, son_gun_ayda=True)
        self.merkez = Sube.objects.create(ad='Merkez Şube', fiyat_grubu='MERKEZ')
        self.fr = Sube.objects.create(ad='Franchise Şube', fiyat_grubu='FRANCHISE')
        # Sevkiyat kataloğu: 12'li koli, taban birim ADET (1 şişe 750 ml)
        self.surup = Urun.objects.create(form='HAMMADDE', kategori='ŞURUP', ad='CARAMEL ŞURUP (750ml)',
                                         koli_icerigi=12, birim='ADET', ust_birim='KOLİ')
        self.stok = StokUrun.objects.create(kategori='ŞURUP VE SOS', ad='CARAMEL ŞURUP', kapali_icerik=750,
                                            acik_carpan=1, sevkiyat_urun=self.surup)

    # ---- yardımcılar
    def sayim(self, sube, ay, kapali=0, acik=0, urun=None):
        urun = urun or self.stok
        sy = StokSayim.objects.create(sube=sube, ay=ay)
        if kapali or acik:
            StokSayimKalem.objects.create(sayim=sy, urun=urun, urun_ad=urun.ad, kapali_icerik=urun.kapali_icerik,
                                          acik_carpan=urun.acik_carpan, kapali_adet=kapali, acik_miktar=acik)
        return sy

    def gelen(self, sube, gun, miktar, birim='ADET', urun=None, saat=12):
        urun = urun or self.surup
        t = SevkiyatTalep.objects.create(sube=sube, durum='Teslim Edildi')
        SevkiyatTalep.objects.filter(pk=t.pk).update(onay_tarih=_zaman(gun, saat))
        SevkiyatKalem.objects.create(talep=t, urun=urun, urun_ad=urun.ad, form='HAMMADDE', koli_icerigi=urun.koli_icerigi,
                                     istenen_miktar=miktar, istenen_birim=birim,
                                     sevkiyat_miktar=miktar, sevkiyat_birim=birim)

    def fiyat(self, deger, gecerli, grup='MERKEZ', sube=None, urun=None):
        TuketimFiyat.objects.create(urun=urun or self.surup, grup='' if sube else grup, sube=sube,
                                    fiyat=Decimal(str(deger)), gecerli=gecerli)

    def satir(self, sube, ay=EKIM, fiyatli=True):
        v = tk.hesapla([sube], ay, fiyatli=fiyatli, ayar=self.ayar)
        c = v['subeler'][0]
        r = next((x for x in c['satirlar'] if x['urun'].id == self.stok.id), None)
        return v, c, r

    # ---- kullanım formülü
    def test_kullanim_acilis_artı_gelen_eksi_kapanis(self):
        self.sayim(self.merkez, EYLUL, kapali=10)                       # 7.500 ml
        self.gelen(self.merkez, D(2026, 10, 10), 1, 'KOLİ')             # 12 şişe = 9.000 ml
        self.sayim(self.merkez, EKIM, kapali=8)                         # 6.000 ml
        _, c, r = self.satir(self.merkez, fiyatli=False)
        self.assertEqual(c['durum'], 'tam')
        self.assertEqual((r['ilk'], r['gelen'], r['son']), (Decimal('7500'), Decimal('9000'), Decimal('6000')))
        self.assertEqual(r['kullanim'], Decimal('10500'))
        self.assertEqual(r['kullanim_taban'], Decimal('14'))            # 14 şişe

    def test_acik_kutu_ve_sifir_kapanis(self):
        self.sayim(self.merkez, EYLUL, kapali=2, acik=300)             # 1.800 ml
        self.sayim(self.merkez, EKIM)                                   # şef hiçbir şey girmedi → 0
        _, _, r = self.satir(self.merkez, fiyatli=False)
        self.assertEqual(r['kullanim'], Decimal('1800'))

    def test_durumlar(self):
        _, c, _ = self.satir(self.merkez, fiyatli=False)
        self.assertEqual(c['durum'], 'acilis_yok')
        self.sayim(self.merkez, EYLUL, kapali=3)
        _, c, r = self.satir(self.merkez, fiyatli=False)
        self.assertEqual(c['durum'], 'sayim_bekleniyor')
        self.assertIsNone(r['kullanim'])
        self.ayar.baslangic = EKIM
        self.ayar.save()
        _, c, _ = self.satir(self.merkez, fiyatli=False)
        self.assertEqual(c['durum'], 'baslamadi')                        # ilk sayım ayı: yalnızca açılış olur

    # ---- ayın son günü kuralı
    def test_ayin_son_gunu_gelen_kurali(self):
        self.sayim(self.merkez, EYLUL, kapali=0)
        self.gelen(self.merkez, D(2026, 9, 30), 12)                     # ayın son günü
        self.gelen(self.merkez, D(2026, 10, 31), 6)                     # ekim son günü
        self.sayim(self.merkez, EKIM, kapali=0)
        _, _, r = self.satir(self.merkez, fiyatli=False)
        self.assertEqual(r['gelen_taban'], Decimal('6'))                 # 30 Eylül eylüle, 31 Ekim ekime yazıldı
        self.ayar.son_gun_ayda = False
        self.ayar.save()
        _, _, r = self.satir(self.merkez, fiyatli=False)
        self.assertEqual(r['gelen_taban'], Decimal('12'))                # 30 Eylül ekime, 31 Ekim kasıma

    def test_baska_subenin_ve_donem_disi_sevkiyat_sayilmaz(self):
        self.sayim(self.merkez, EYLUL, kapali=1)
        self.gelen(self.fr, D(2026, 10, 5), 12)
        self.gelen(self.merkez, D(2026, 11, 2), 12)
        self.gelen(self.merkez, D(2026, 9, 10), 12)
        self.sayim(self.merkez, EKIM, kapali=1)
        _, _, r = self.satir(self.merkez, fiyatli=False)
        self.assertEqual(r['gelen_taban'], Decimal('0'))

    def test_onaylanmamis_sevkiyat_sayilmaz(self):
        self.sayim(self.merkez, EYLUL, kapali=1)
        t = SevkiyatTalep.objects.create(sube=self.merkez, durum='Sevkiyatta')
        SevkiyatKalem.objects.create(talep=t, urun=self.surup, urun_ad=self.surup.ad, form='HAMMADDE',
                                     istenen_miktar=5, istenen_birim='ADET')
        self.sayim(self.merkez, EKIM, kapali=1)
        _, _, r = self.satir(self.merkez, fiyatli=False)
        self.assertEqual(r['gelen_taban'], Decimal('0'))

    # ---- maliyet
    def test_maliyet_tek_fiyat(self):
        self.fiyat(100, D(2026, 1, 1))
        self.sayim(self.merkez, EYLUL, kapali=10)
        self.gelen(self.merkez, D(2026, 10, 10), 12)
        self.sayim(self.merkez, EKIM, kapali=8)
        _, c, r = self.satir(self.merkez)
        self.assertEqual(r['kullanim_taban'], Decimal('14'))
        self.assertEqual(r['birim_maliyet'], Decimal('100.0000'))
        self.assertEqual(r['tutar'], Decimal('1400.00'))
        self.assertEqual(c['tutar'], Decimal('1400.00'))

    def test_ay_ortasi_fiyat_degisikligi_agirlikli_ortalama(self):
        self.fiyat(100, D(2026, 1, 1))
        self.fiyat(120, D(2026, 10, 15))
        self.sayim(self.merkez, EYLUL, kapali=10)                        # açılış 10 şişe @100
        self.gelen(self.merkez, D(2026, 10, 10), 6)                      # @100
        self.gelen(self.merkez, D(2026, 10, 20), 6)                      # @120
        self.sayim(self.merkez, EKIM, kapali=8)                          # kullanım 14 şişe
        _, _, r = self.satir(self.merkez)
        ort = (Decimal(10) * 100 + 6 * 100 + 6 * 120) / Decimal(22)
        self.assertEqual(r['birim_maliyet'], ort.quantize(Decimal('0.0001')))
        self.assertEqual(r['tutar'], (14 * ort).quantize(Decimal('0.01')))

    def test_fiyat_grubu_ve_sube_istisnasi(self):
        self.fiyat(100, D(2026, 1, 1), grup='MERKEZ')
        self.fiyat(130, D(2026, 1, 1), grup='FRANCHISE')
        for s in (self.merkez, self.fr):
            self.sayim(s, EYLUL, kapali=10)
            self.sayim(s, EKIM, kapali=6)                                # 4 şişe kullanım, gelen yok
        _, _, r1 = self.satir(self.merkez)
        _, _, r2 = self.satir(self.fr)
        self.assertEqual((r1['tutar'], r2['tutar']), (Decimal('400.00'), Decimal('520.00')))
        self.fiyat(110, D(2026, 1, 1), sube=self.fr)                     # şubeye özel fiyat grubun önüne geçer
        _, _, r2 = self.satir(self.fr)
        self.assertEqual(r2['tutar'], Decimal('440.00'))

    def test_fiyat_yoksa_eksik_isaretlenir_ve_eslesmeyen_listelenir(self):
        self.sayim(self.merkez, EYLUL, kapali=10)
        self.sayim(self.merkez, EKIM, kapali=6)
        v, c, r = self.satir(self.merkez)
        self.assertTrue(r['fiyat_eksik'])
        self.assertIsNone(r['tutar'])
        self.assertIn('CARAMEL ŞURUP', ' '.join(v['fiyat_eksik']).upper())
        yeni = Urun.objects.create(form='HAMMADDE', kategori='X', ad='EŞLEŞMEYEN ÜRÜN', koli_icerigi=1, birim='ADET', ust_birim='')
        self.gelen(self.merkez, D(2026, 10, 4), 3, urun=yeni)
        v, _, _ = self.satir(self.merkez)
        self.assertEqual([e['ad'] for e in v['eslesmeyen']], ['EŞLEŞMEYEN ÜRÜN'])

    def test_kg_ile_gelen_gramla_sayilan_urun(self):
        kahve = Urun.objects.create(form='HAMMADDE', kategori='KAHVE', ad='ESPRESSO KAHVE ÇEKİRDEĞİ', koli_icerigi=15,
                                    birim='KG', ust_birim='')
        su = StokUrun.objects.create(kategori='KAHVE VE TOZ', ad='ESPRESSO ÇEKİRDEK', kapali_icerik=1000, sevkiyat_urun=kahve)
        self.assertEqual(tk.carpan(su), Decimal('1000'))
        self.sayim(self.merkez, EYLUL, kapali=5, urun=su)                # 5.000 gr
        self.gelen(self.merkez, D(2026, 10, 3), 15, 'KG', urun=kahve)     # 15 kg = 15.000 gr
        self.sayim(self.merkez, EKIM, kapali=8, urun=su)                  # 8.000 gr
        self.fiyat(400, D(2026, 1, 1), urun=kahve)                        # 400 TL / kg
        v = tk.hesapla([self.merkez], EKIM, fiyatli=True, ayar=self.ayar)
        r = next(x for x in v['subeler'][0]['satirlar'] if x['urun'].id == su.id)
        self.assertEqual(r['kullanim'], Decimal('12000'))                # gr
        self.assertEqual(r['kullanim_taban'], Decimal('12'))             # kg
        self.assertEqual(r['tutar'], Decimal('4800.00'))

    def test_negatif_kullanim_uyarisi(self):
        self.sayim(self.merkez, EYLUL, kapali=2)
        self.sayim(self.merkez, EKIM, kapali=5)
        _, _, r = self.satir(self.merkez, fiyatli=False)
        self.assertLess(r['kullanim'], 0)
        self.assertTrue(r['uyari'])

    # ---- seri
    def test_aylik_seri(self):
        self.fiyat(100, D(2026, 1, 1))
        self.sayim(self.merkez, D(2026, 8, 1), kapali=10)
        self.sayim(self.merkez, EYLUL, kapali=8)
        self.sayim(self.merkez, EKIM, kapali=5)
        s = tk.aylik_seri([self.merkez], EKIM, adet=3, ayar=self.ayar)
        self.assertEqual(s['etiketler'], ['Ağustos 2026', 'Eylül 2026', 'Ekim 2026'])
        self.assertEqual(s['seri'][self.merkez.id], [None, Decimal('200.00'), Decimal('300.00')])
        self.assertEqual(s['toplam'], [None, Decimal('200.00'), Decimal('300.00')])

    # ---- görünürlük
    def test_rapor_subeleri_kapsami(self):
        bm = kisi(Rol.MUDUR, None, 'BM')
        bm.sorumlu_subeler.add(self.merkez)
        self.assertEqual([s.id for s in tk.rapor_subeleri(bm)], [self.merkez.id])
        sef = kisi(Rol.SEF, self.fr, 'Şef')
        self.assertEqual([s.id for s in tk.rapor_subeleri(sef)], [self.fr.id])
        for rol in (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI, Rol.SATIN_ALMA):
            self.assertEqual({s.id for s in tk.rapor_subeleri(kisi(rol, None, 'x' + rol))}, {self.merkez.id, self.fr.id})
        self.assertEqual(tk.rapor_subeleri(kisi(Rol.PERSONEL, self.fr, 'p')), [])

    # ---- eşleme önerisi
    def test_esleme_onerisi_parantezi_yok_sayar(self):
        diger = Urun.objects.create(form='HAMMADDE', kategori='ŞURUP', ad='CARAMEL SOS (2.000ml)', koli_icerigi=3, birim='ADET', ust_birim='KOLİ')
        yeni = StokUrun.objects.create(kategori='ŞURUP VE SOS', ad='CARAMEL SOS', kapali_icerik=2000)
        oneri = tk.esleme_oner([yeni, self.stok], list(Urun.objects.all()))
        self.assertEqual(oneri[yeni.id][0].id, diger.id)
        self.assertEqual(oneri[self.stok.id][0].id, self.surup.id)


@override_settings(**_AYAR)
class TuketimSayfaTesti(TestCase):
    """Sayfa yetkileri: kim neyi görür, fiyat kimden saklanır."""

    def setUp(self):
        TuketimAyar.objects.all().delete()
        TuketimAyar.objects.create(aktif=True, baslangic=None, son_gun_ayda=True)
        self.a = Sube.objects.create(ad='Alfa Şube', fiyat_grubu='MERKEZ')
        self.b = Sube.objects.create(ad='Beta Şube', fiyat_grubu='FRANCHISE')
        self.urun = Urun.objects.create(form='HAMMADDE', kategori='ŞURUP', ad='VANILYA ŞURUP (750ml)',
                                        koli_icerigi=12, birim='ADET', ust_birim='KOLİ')
        self.stok = StokUrun.objects.create(kategori='ŞURUP VE SOS', ad='VANILYA ŞURUP', kapali_icerik=750,
                                            acik_carpan=1, sevkiyat_urun=self.urun)
        for sube, bos in ((self.a, 8), (self.b, 5)):
            for ay, adet in ((EYLUL, 10), (EKIM, bos)):
                sy = StokSayim.objects.create(sube=sube, ay=ay)
                StokSayimKalem.objects.create(sayim=sy, urun=self.stok, urun_ad=self.stok.ad, kapali_icerik=750,
                                              acik_carpan=1, kapali_adet=adet)
        TuketimFiyat.objects.create(urun=self.urun, grup='MERKEZ', fiyat=Decimal('111.11'), gecerli=D(2026, 1, 1))
        TuketimFiyat.objects.create(urun=self.urun, grup='FRANCHISE', fiyat=Decimal('333.33'), gecerli=D(2026, 1, 1))
        self.url = reverse('tuketim_rapor') + '?ay=2026-10'

    def gir(self, rol, sube=None):
        p = kisi(rol, sube)
        self.client.force_login(p.user)
        return p

    def test_sef_yalniz_kendi_subesi_ve_fiyati(self):
        self.gir(Rol.SEF, self.a)
        r = self.client.get(self.url + '&sube=%d' % self.b.id)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Alfa Şube')
        self.assertNotContains(r, 'Beta Şube')
        self.assertContains(r, '111')
        self.assertNotContains(r, '333,33')
        self.assertNotContains(r, '333.33')

    def test_magaza_muduru_kendi_subesi(self):
        self.gir(Rol.MAGAZA_MUDURU, self.b)
        r = self.client.get(self.url)
        self.assertContains(r, 'Beta Şube')
        self.assertNotContains(r, 'Alfa Şube')

    def test_bolge_muduru_yalniz_sorumlu_subeler(self):
        p = self.gir(Rol.MUDUR)
        p.sorumlu_subeler.add(self.a)
        r = self.client.get(self.url)
        self.assertContains(r, 'Alfa Şube')
        self.assertNotContains(r, 'Beta Şube')

    def test_yatirimci_ve_yonetim_hepsini_gorur(self):
        for rol in (Rol.YATIRIMCI, Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.SATIN_ALMA):
            self.gir(rol)
            r = self.client.get(self.url)
            self.assertContains(r, 'Alfa Şube'); self.assertContains(r, 'Beta Şube')

    def test_fiyat_esleme_ayar_sayfalari_yetkisi(self):
        for rol in (Rol.SEF, Rol.MAGAZA_MUDURU, Rol.MUDUR, Rol.YATIRIMCI):
            self.gir(rol, self.a)
            for ad in ('tuketim_fiyatlar', 'tuketim_esleme', 'tuketim_ayar'):
                r = self.client.get(reverse(ad))
                self.assertEqual(r.status_code, 302, (rol, ad))
        for rol in (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.SATIN_ALMA):
            self.gir(rol)
            for ad in ('tuketim_fiyatlar', 'tuketim_esleme'):
                self.assertEqual(self.client.get(reverse(ad)).status_code, 200, (rol, ad))
        self.gir(Rol.SATIN_ALMA)
        self.assertEqual(self.client.get(reverse('tuketim_ayar')).status_code, 302)   # ayar: GM/Operatör
        self.gir(Rol.GENEL_MUDUR)
        self.assertEqual(self.client.get(reverse('tuketim_ayar')).status_code, 200)

    def test_sistem_kapaliyken(self):
        TuketimAyar.objects.update(aktif=False)
        self.gir(Rol.SEF, self.a)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'Ürün bazında kullanım')
        self.gir(Rol.GENEL_MUDUR)
        self.assertContains(self.client.get(self.url), 'Ürün bazında kullanım')

    def test_fiyat_yazma_ve_menu(self):
        self.gir(Rol.SATIN_ALMA)
        r = self.client.post(reverse('tuketim_fiyat_detay', args=[self.urun.id]),
                             {'islem': 'ekle', 'hedef': 'MERKEZ', 'fiyat': '125,5', 'tarih': '2026-10-15'})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(TuketimFiyat.objects.filter(urun=self.urun, grup='MERKEZ', fiyat=Decimal('125.5')).exists())
        self.assertContains(self.client.get(reverse('tuketim_fiyatlar')), 'VANILYA')
        self.assertContains(self.client.get(reverse('ana_sayfa'), follow=True), 'Tüketim')

    def test_aylik_grafik_ve_toplam(self):
        self.gir(Rol.GENEL_MUDUR)
        r = self.client.get(self.url)
        self.assertEqual(r.context['veri']['tam_sube'], 2)
        # Alfa: 2 şişe × 111,11 ; Beta: 5 şişe × 333,33
        self.assertEqual(r.context['veri']['genel_tutar'], Decimal('2') * Decimal('111.11') + 5 * Decimal('333.33'))
        self.assertTrue(r.context['top_kalemler'])
        self.assertEqual(len(r.context['sube_sutun']), 2)

    # ---- indirme
    def test_aylik_excel_pdf(self):
        import io, openpyxl
        self.gir(Rol.GENEL_MUDUR)
        r = self.client.get(reverse('tuketim_indir') + '?tur=ay&ay=2026-10&bicim=xlsx')
        self.assertEqual(r.status_code, 200)
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        self.assertEqual(wb.sheetnames, ['Şube özeti', 'Ürün toplamı', 'Şube × ürün'])
        r = self.client.get(reverse('tuketim_indir') + '?tur=ay&ay=2026-10&bicim=pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))

    def test_gelen_mal_gun_hafta_ozel(self):
        import io, openpyxl
        t = SevkiyatTalep.objects.create(sube=self.a, durum='Teslim Edildi')
        SevkiyatTalep.objects.filter(pk=t.pk).update(onay_tarih=_zaman(D(2026, 10, 14)))
        SevkiyatKalem.objects.create(talep=t, urun=self.urun, urun_ad=self.urun.ad, form='HAMMADDE', koli_icerigi=12,
                                     istenen_miktar=1, istenen_birim='KOLİ', sevkiyat_miktar=1, sevkiyat_birim='KOLİ')
        self.gir(Rol.OPERATOR)
        g = lambda **k: self.client.get(reverse('tuketim_indir'), dict(tur='gelen', bicim='xlsx', **k))
        for q in (dict(aralik='gun', ref='2026-10-14'), dict(aralik='hafta', ref='2026-10-16'),
                  dict(aralik='ozel', bas='2026-10-10', bit='2026-10-20'), dict(aralik='ay', ref='2026-10-01')):
            ws = openpyxl.load_workbook(io.BytesIO(g(**q).content))['Gün gün']
            self.assertEqual(ws.cell(row=6, column=2).value, 'Alfa Şube', q)
            self.assertAlmostEqual(ws.cell(row=7, column=7).value, 12 * 111.11, places=1)   # toplam satırı
        ws = openpyxl.load_workbook(io.BytesIO(g(aralik='gun', ref='2026-10-15').content))['Gün gün']
        self.assertIsNone(ws.cell(row=6, column=2).value if ws.cell(row=6, column=1).value != 'TOPLAM' else None)
        self.assertTrue(self.client.get(reverse('tuketim_indir'), dict(tur='gelen', bicim='pdf', aralik='hafta')).content.startswith(b'%PDF'))

    def test_indirmede_kapsam(self):
        import io, openpyxl
        self.gir(Rol.SEF, self.a)
        r = self.client.get(reverse('tuketim_indir') + '?tur=ay&ay=2026-10&bicim=xlsx&sube=%d' % self.b.id)
        ws = openpyxl.load_workbook(io.BytesIO(r.content))['Şube özeti']
        adlar = [ws.cell(row=i, column=1).value for i in range(6, 9)]
        self.assertIn('Alfa Şube', adlar); self.assertNotIn('Beta Şube', adlar)

    def test_fiyat_gruplari_ayardan(self):
        self.gir(Rol.OPERATOR)
        r = self.client.post(reverse('tuketim_ayar'), {'islem': 'gruplar', 'g_%d' % self.a.id: 'FRANCHISE', 'g_%d' % self.b.id: 'MERKEZ'})
        self.assertEqual(r.status_code, 302)
        self.a.refresh_from_db(); self.b.refresh_from_db()
        self.assertEqual((self.a.fiyat_grubu, self.b.fiyat_grubu), ('FRANCHISE', 'MERKEZ'))
        self.assertContains(self.client.get(reverse('tuketim_ayar')), 'Şube fiyat grupları')
