import datetime
from unittest import mock

import requests

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings

from . import menulux as mx
from . import satis_views as sv
from .models import MenuluxOnbellek, Personel, Rol, Sube

ENV = {'MENULUX_USER': 'u@x.com', 'MENULUX_PASS': 'gizli', 'MENULUX_CUSTOMER_ID': '100'}
BRANCHES = [{'CustomerID': 100, 'Name': 'MERKEZ', 'Deleted': False}, {'CustomerID': 1, 'Name': 'GEEK-1 (NACİ TOPÇUOĞLU)', 'Deleted': False},
            {'CustomerID': 2, 'Name': 'GEEK-2 (OSMANGAZİ)', 'Deleted': False}, {'CustomerID': 3, 'Name': 'ESKİ ŞUBE', 'Deleted': True}]


def eod(ciro, adisyon):
    return {'SessionCount': adisyon, 'GuestCount': adisyon, 'SessionTotalPrice': ciro, 'SessionOrderPrice': ciro + 10, 'CashPrice': ciro / 2,
            'CreditPrice': ciro / 2, 'GiftedPrice': 5, 'CancelledPrice': 1, 'ReturnedPrice': 2, 'SessionTotalDiscount': 3, 'SessionTaxPrice': 9}


def sahte_get(yol, **p):
    cid = p.get('customerID')
    if yol == 'CustomerAPI/GetSortedBranches':
        return BRANCHES
    if yol == 'ReportAPI/GetEndOfDayReport':
        return {100: eod(1000, 10), 1: eod(400, 4), 2: eod(600, 6)}[cid]
    if yol in ('ReportAPI/GetProductSalesReportDb', 'ReportAPI/GetOrderSalesReportBranchesDb'):
        taban = [{'ProductID': 1, 'Name': 'Latte', 'Code': 'A1', 'GroupName': 'KAHVE', 'Quantity': 3, 'TotalPrice': 300, 'TaxPrice': 27},
                 {'ProductID': 9, 'Name': 'İade ürün', 'Code': 'Z', 'Quantity': 1, 'TotalPrice': 5, 'Returned': True}]
        return taban if cid != 2 else [dict(taban[0], Quantity=2, TotalPrice=200)]
    if yol in ('ReportAPI/GetCategorySalesReport',):
        return [{'GroupID': 5, 'Name': 'KAHVE', 'Quantity': 5, 'NetPrice': 450, 'TaxPrice': 50, 'TotalPrice': 500}]
    if yol == 'ReportAPI/GetCategorySalesReportBranch':
        return [{'CustomerID': 1, 'GroupID': 5, 'Name': 'KAHVE', 'Quantity': 3, 'NetPrice': 270, 'TaxPrice': 30, 'TotalPrice': 300},
                {'CustomerID': 2, 'GroupID': 5, 'Name': 'KAHVE', 'Quantity': 2, 'NetPrice': 180, 'TaxPrice': 20, 'TotalPrice': 200}]
    if yol == 'MenuAPI/GetMenusSummary':
        return [{'MenuID': 7, 'Name': 'M', 'Dafault': True}]
    if yol == 'OfferAPI/GetProducts':
        return [{'ProductID': 1, 'Name': 'Latte', 'Code': 'A1', 'GroupName': 'KAHVE', 'Price': 100},
                {'ProductID': 2, 'Name': 'Mocha', 'Code': 'A2', 'GroupName': 'KAHVE', 'Price': 120}]
    raise AssertionError(yol)


class _Taban(TestCase):
    def setUp(self):
        cache.clear(); mx.oturumu_sifirla()
        self.env = mock.patch.dict('os.environ', ENV); self.env.start()
        self.get = mock.patch.object(mx, '_get', side_effect=sahte_get); self.get.start()
        self.ak = mock.patch.object(mx, '_authkey', return_value='K'); self.ak.start()
        self.s1 = Sube.objects.create(ad='Geek-1 (Naci Topçuoğlu)', menulux_id=1)
        self.s2 = Sube.objects.create(ad='Geek-2 Osmangazi', menulux_id=2)
        self.s3 = Sube.objects.create(ad='Eşleşmemiş')

    def tearDown(self):
        self.env.stop(); self.get.stop(); self.ak.stop()

    def giris(self, rol, sube=None, sorumlu=()):
        u = User.objects.create(username='k_%s_%d' % (rol, User.objects.count()))
        p = Personel.objects.create(user=u, ad_soyad=rol, rol=rol, sube=sube)
        p.sorumlu_subeler.set(sorumlu)
        self.client.force_login(u)
        return p


class MenuluxIstemciTest(_Taban):
    def test_donem_oku(self):
        b = datetime.date(2026, 10, 14)   # çarşamba
        self.assertEqual(sv.donem_oku('hafta', bugun=b), (datetime.date(2026, 10, 12), b))
        self.assertEqual(sv.donem_oku('gecen_hafta', bugun=b), (datetime.date(2026, 10, 5), datetime.date(2026, 10, 11)))
        self.assertEqual(sv.donem_oku('gecen_ay', bugun=b), (datetime.date(2026, 9, 1), datetime.date(2026, 9, 30)))
        self.assertEqual(sv.donem_oku('ozel', datetime.date(2026, 3, 5), datetime.date(2026, 3, 1)), (datetime.date(2026, 3, 1), datetime.date(2026, 3, 5)))

    def test_rapor_tum_sube(self):
        v = mx.rapor('tum', datetime.date(2026, 10, 1), datetime.date(2026, 10, 3))
        self.assertEqual(v['ozet']['ciro'], 1000)
        self.assertEqual([s['ad'] for s in v['subeler']], ['GEEK-2 (OSMANGAZİ)', 'GEEK-1 (NACİ TOPÇUOĞLU)'])   # ciroya göre, silinen şube yok
        self.assertEqual(len(v['gunluk']), 3)
        self.assertEqual(v['urunler'][0]['adet'], 3)                     # iade satırı satış sayılmaz
        self.assertEqual([u['ad'] for u in v['satilmayan']], ['Mocha'])
        self.assertAlmostEqual(v['ozet']['ort'], 100)

    def test_rapor_coklu_sube_toplar(self):
        v = mx.rapor([1, 2], datetime.date(2026, 10, 1), datetime.date(2026, 10, 1))
        self.assertEqual(v['ozet']['ciro'], 1000); self.assertEqual(v['urunler'][0]['adet'], 5)
        self.assertEqual(v['kategoriler'][0]['tutar'], 500); self.assertEqual(v['gunluk'], [])   # tek gün: günlük döküm yok

    def test_onbellek_kullanilir(self):
        d = datetime.date(2026, 1, 1)
        mx.ozet(1, d, d); mx.ozet(1, d, d)
        self.assertEqual(sum(1 for c in mx._get.call_args_list if c.args[0] == 'ReportAPI/GetEndOfDayReport'), 1)
        self.assertTrue(MenuluxOnbellek.objects.exists())


class MenuluxGirisTest(TestCase):
    def setUp(self):
        mx.oturumu_sifirla(); self.env = mock.patch.dict('os.environ', ENV); self.env.start()

    def tearDown(self):
        self.env.stop()

    def _yanit(self, status=200, json=None, headers=None):
        r = mock.Mock(); r.status_code = status; r.json.return_value = json; r.headers = headers or {}; return r

    def test_giris_akisi_ve_yeniden_giris(self):
        anahtarlar = iter(['K1', 'K2'])
        with mock.patch('requests.Session') as S, mock.patch('requests.get') as G:
            S.return_value.get.return_value = self._yanit(json={'PublicKey': 'PK'})
            S.return_value.post.side_effect = lambda *a, **k: self._yanit(headers={'AuthKey': next(anahtarlar)})
            G.side_effect = [self._yanit(401), self._yanit(json=[1])]
            self.assertEqual(mx._get('ReportAPI/X', customerID=1), [1])
        post = S.return_value.post.call_args_list[0]
        self.assertEqual(post.kwargs['headers']['Publickey'], 'PK')
        self.assertEqual(post.kwargs['json']['Password'], 'gizli')
        self.assertEqual(G.call_args_list[0].kwargs['headers']['AuthKey'], 'K1')
        self.assertEqual(G.call_args_list[1].kwargs['headers']['AuthKey'], 'K2')      # 401 sonrası yeniden giriş
        self.assertEqual(G.call_args_list[0].kwargs['headers']['CustomerID'], '100')

    def test_authkey_veritabanindan_paylasilir(self):
        with mock.patch('requests.Session') as S, mock.patch('requests.get') as G:
            S.return_value.get.return_value = self._yanit(json={'PublicKey': 'PK'})
            S.return_value.post.return_value = self._yanit(headers={'AuthKey': 'PAYLASILAN'})
            G.return_value = self._yanit(json=[])
            mx._get('A')                                   # ilk işçi girer ve anahtarı veritabanına yazar
            mx._oturum['authkey'] = None                   # ikinci işçi: bellek boş
            mx._get('B')
        self.assertEqual(S.return_value.post.call_count, 1)   # ikinci işçi yeniden giriş yapmadı
        self.assertEqual(G.call_args_list[1].kwargs['headers']['AuthKey'], 'PAYLASILAN')

    def test_json_olmayan_yanit_teshis_verir(self):
        with mock.patch('requests.Session') as S:
            r = self._yanit(status=403); r.json.side_effect = requests.exceptions.JSONDecodeError('x', 'doc', 0); r.text = '<html>Access denied</html>'
            S.return_value.get.return_value = r
            with self.assertRaises(mx.MenuluxHata) as c:
                mx._get('x')
        self.assertIn('HTTP 403', str(c.exception)); self.assertIn('Access denied', str(c.exception)); self.assertNotIn('gizli', str(c.exception))

    def test_giris_once_login_sayfasini_acar(self):
        with mock.patch('requests.Session') as S, mock.patch('requests.get') as G:
            S.return_value.get.return_value = self._yanit(json={'PublicKey': 'PK'})
            S.return_value.post.return_value = self._yanit(headers={'AuthKey': 'K'})
            G.return_value = self._yanit(json=[])
            mx._get('x')
        urller = [c.args[0] for c in S.return_value.get.call_args_list]
        self.assertTrue(urller[0].endswith('/Account/Login') and urller[1].endswith('/GeneratePublicKey'))
        self.assertIn('Mozilla', S.return_value.headers.update.call_args.args[0]['User-Agent'])

    def test_sms_istenirse_anlasilir_hata(self):
        with mock.patch('requests.Session') as S:
            S.return_value.get.return_value = self._yanit(json={'PublicKey': 'PK'})
            S.return_value.post.return_value = self._yanit(status=202)
            with self.assertRaises(mx.MenuluxHata):
                mx._get('x')

    def test_hata_mesajinda_sifre_yok(self):
        with mock.patch('requests.Session') as S:
            S.return_value.get.return_value = self._yanit(json={'PublicKey': 'PK'})
            S.return_value.post.return_value = self._yanit(status=500)
            try:
                mx._get('x')
            except mx.MenuluxHata as e:
                self.assertNotIn('gizli', str(e))


class SatisEkranTest(_Taban):
    def test_giris_yapmamis_yonlendirilir(self):
        self.assertEqual(self.client.get('/satis/').status_code, 302)

    def test_yetkisiz_rol(self):
        self.giris(Rol.PERSONEL, self.s1)
        self.assertEqual(self.client.get('/satis/').status_code, 302)
        self.assertEqual(self.client.get('/satis/indir/').status_code, 302)

    def test_yonetim_tum_subeleri_gorur(self):
        for rol in (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI, Rol.SATIN_ALMA):
            self.client.logout(); self.giris(rol)
            r = self.client.get('/satis/?donem=ay')
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, 'GEEK-2 (OSMANGAZİ)'); self.assertContains(r, 'Tüm şubeler')
            self.assertContains(r, 'Mocha')

    def test_sef_yalniz_kendi_subesi(self):
        self.giris(Rol.SEF, self.s1)
        r = self.client.get('/satis/?sube=2')            # başka şubeyi zorlasa da kendi şubesine düşer
        self.assertEqual([x[1] for x in r.context['secenekler']], [self.s1.ad])
        ciro = [c for c in mx._get.call_args_list if c.args[0] == 'ReportAPI/GetEndOfDayReport']
        self.assertTrue(all(c.kwargs['customerID'] == 1 for c in ciro))

    def test_bolge_muduru_sorumlu_subeler(self):
        self.giris(Rol.MUDUR, None, [self.s1, self.s2, self.s3])
        r = self.client.get('/satis/')
        self.assertContains(r, 'Tüm sorumlu şubelerim')
        self.assertEqual([x[1] for x in r.context['secenekler']], ['Tüm sorumlu şubelerim', self.s1.ad, self.s2.ad])   # menulux_id'si olmayan şube yok

    def test_eslesmemis_sef_uyari_gorur(self):
        self.giris(Rol.SEF, self.s3)
        self.assertContains(self.client.get('/satis/'), 'eşleştirmesi yapılmamış')

    def test_ayar_yoksa_uyari(self):
        self.giris(Rol.GENEL_MUDUR)
        with mock.patch.dict('os.environ', {'MENULUX_USER': '', 'MENULUX_PASS': ''}):
            self.assertContains(self.client.get('/satis/'), 'MENULUX_USER')

    def test_menulux_hatasi_sayfayi_dusurmez(self):
        self.giris(Rol.GENEL_MUDUR)
        with mock.patch.object(mx, '_get', side_effect=mx.MenuluxHata('Menulux\'a ulaşılamadı.')):
            r = self.client.get('/satis/')
        self.assertEqual(r.status_code, 200); self.assertContains(r, 'ulaşılamadı')

    def test_excel_ve_pdf(self):
        self.giris(Rol.GENEL_MUDUR)
        r = self.client.get('/satis/indir/?sube=tum&donem=ay&bicim=xlsx')
        self.assertEqual(r.status_code, 200); self.assertTrue(r.content.startswith(b'PK'))
        import io, openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        self.assertEqual(wb.sheetnames, ['Özet', 'Şubeler', 'Günlük', 'Kategoriler', 'Satan ürünler', 'Satılmayan'])
        r = self.client.get('/satis/indir/?sube=tum&donem=ay&bicim=pdf')
        self.assertEqual(r.status_code, 200); self.assertTrue(r.content.startswith(b'%PDF'))

    def test_sef_baska_subenin_dosyasini_indiremez(self):
        self.giris(Rol.SEF, self.s1)
        self.client.get('/satis/indir/?sube=2&donem=bugun&bicim=xlsx')
        ciro = [c for c in mx._get.call_args_list if c.args[0] == 'ReportAPI/GetEndOfDayReport']
        self.assertTrue(ciro and all(c.kwargs['customerID'] == 1 for c in ciro))

    def test_eslestirme_yetki_ve_kayit(self):
        self.giris(Rol.SEF, self.s1)
        self.assertEqual(self.client.get('/satis/eslestirme/').status_code, 302)
        self.client.logout(); self.giris(Rol.GENEL_MUDUR)
        r = self.client.get('/satis/eslestirme/'); self.assertEqual(r.status_code, 200)
        yeni = Sube.objects.create(ad='Geek 2 Osmangazi Yeni')
        self.assertEqual(mx.eslestirme_onerisi([yeni, self.s3], mx.subeler()), {yeni.id: 2})   # ad benzerliğinden öneri; alakasız ad önerilmez
        r = self.client.post('/satis/eslestirme/', {'s%d' % self.s1.id: '2', 's%d' % self.s2.id: '1'})
        self.s1.refresh_from_db(); self.s2.refresh_from_db()
        self.assertEqual((self.s1.menulux_id, self.s2.menulux_id), (2, 1))          # yer değiştirme unique'e takılmaz
        r = self.client.post('/satis/eslestirme/', {'s%d' % self.s1.id: '1', 's%d' % self.s2.id: '1'})
        self.s1.refresh_from_db(); self.assertEqual(self.s1.menulux_id, 2)          # çift atama reddedilir
        r = self.client.post('/satis/eslestirme/', {'s%d' % self.s1.id: '999'})
        self.s1.refresh_from_db(); self.assertEqual(self.s1.menulux_id, 2)          # geçersiz numara reddedilir

    def test_tablo_haftalik_gorunum(self):
        self.giris(Rol.GENEL_MUDUR)
        r = self.client.get('/satis/tablo/?gorunum=hafta&sube=tum&ref=2026-10-14&hafta=4')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['donem_satirlari']), 4)
        self.assertEqual(r.context['donem_satirlari'][3]['ozet']['ciro'], 1000)      # 4. hafta: 2026-10-12 – 10-18, mock sabit 1000
        self.assertEqual(r.context['toplam']['ciro'], 4000)                           # 4 hafta × 1000
        self.assertContains(r, '4. Hafta'); self.assertContains(r, 'GEEK-2 (OSMANGAZİ)')

    def test_tablo_aylik_gorunum_ve_matris(self):
        self.giris(Rol.GENEL_MUDUR)
        r = self.client.get('/satis/tablo/?gorunum=ay&sube=tum&yil=2026&ay=3')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['donem_satirlari']), 12)
        self.assertEqual(r.context['toplam']['ciro'], 12000)                          # 12 ay × 1000
        matris = {r2['ad']: r2 for r2 in r.context['kategori_matris_tutar']}
        self.assertEqual(matris['KAHVE']['toplam'], 500 * 12)                         # her ay sabit 500
        self.assertEqual(len(matris['KAHVE']['degerler']), 12)
        self.assertContains(r, 'Mar'); self.assertContains(r, 'kategori × ay')

    def test_tablo_sef_tek_sube(self):
        self.giris(Rol.SEF, self.s1)
        r = self.client.get('/satis/tablo/?gorunum=hafta&ref=2026-10-14')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['subeler'], [])                                    # tek şube: karşılaştırma yok
        self.assertNotContains(r, 'Şube karşılaştırması')

    def test_tablo_yetkisiz(self):
        self.giris(Rol.PERSONEL, self.s1)
        self.assertEqual(self.client.get('/satis/tablo/').status_code, 302)

    def test_rapor_sayfasinda_tablo_linki_var(self):
        self.giris(Rol.GENEL_MUDUR)
        self.assertContains(self.client.get('/satis/'), 'Tablo görünümü')

    def test_menude_gorunur(self):
        self.giris(Rol.YATIRIMCI)
        self.assertContains(self.client.get('/satis/'), 'Satış Raporları')

    def test_satin_alma_tum_subeleri_gorur(self):
        self.giris(Rol.SATIN_ALMA)
        r = self.client.get('/satis/?donem=ay')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'GEEK-2 (OSMANGAZİ)'); self.assertContains(r, 'Tüm şubeler')
