"""Canlı Google Sheet (yayınlanmış CSV) -> Geek Panel QR Menü.

Excel dosyaları KULLANILMAZ (eski kopyalar). Kaynak, QR sitelerinin okuduğu canlı
Sheet CSV adresleridir (bkz. panel/menu_sema.py).

Kullanım:
    python manage.py menu_aktar --dry-run                 # hiçbir şey yazmadan rapor
    python manage.py menu_aktar                           # iki markayı içeri al (yeni olanları ekler)
    python manage.py menu_aktar --marka baga --dry-run
    python manage.py menu_aktar --guncelle                # mevcut ürünleri de CSV değerleriyle EZER
    python manage.py menu_aktar --yayinla                 # içeri aldıktan sonra CSV'yi R2'ye yayınla
    python manage.py menu_aktar --marka geek --dosya geek.csv   # internet yerine yerel CSV

İdempotent: ürün anahtarı (marka, kod). Varsayılan olarak mevcut ürünlere dokunmaz;
panelden yapılan düzenlemeler ancak --guncelle ile ezilir. Görsel linkleri (Drive lh3)
olduğu gibi `gorsel_harici` alanına yazılır; panelden yüklenen fotoğraflara dokunulmaz.
"""
import csv
import io
import re
import urllib.request
from collections import Counter, OrderedDict
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from panel.menu_sema import MARKALAR
from panel.menu_views import tr_slug
from panel.models import MenuKategori, MenuMarka, MenuUrun


def _normalize_kod(s):
    """QR sitesindeki normalizeCode ile aynı: TR küçük harf + yalnızca [a-z0-9]."""
    s = str(s or '').strip().lower()
    for a, b in (('ı', 'i'), ('ğ', 'g'), ('ü', 'u'), ('ş', 's'), ('ö', 'o'), ('ç', 'c')):
        s = s.replace(a, b)
    return re.sub(r'[^a-z0-9]+', '', s)


def _dogru(v):
    return str(v or '').strip().upper() == 'TRUE'


def _ondalik(v):
    s = str(v or '').strip().replace(',', '.')
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


class Command(BaseCommand):
    help = "Canlı Google Sheet CSV'lerinden Geek/Baga QR menü ürünlerini ve kategorilerini içeri alır."

    def add_arguments(self, parser):
        parser.add_argument('--marka', choices=['geek', 'baga', 'hepsi'], default='hepsi')
        parser.add_argument('--dry-run', action='store_true', help='Hiçbir şey yazma; sadece rapor ver.')
        parser.add_argument('--guncelle', action='store_true',
                            help='Mevcut ürünleri/kategori adlarını CSV değerleriyle güncelle (panel düzenlemelerini ezer).')
        parser.add_argument('--yayinla', action='store_true', help="Aktarımdan sonra marka CSV'sini R2'ye yayınla.")
        parser.add_argument('--dosya', help='İnternet yerine yerel CSV dosyası (yalnızca tek --marka ile).')

    # ------------------------------------------------------------------ giriş
    def handle(self, *args, **o):
        markalar = ['geek', 'baga'] if o['marka'] == 'hepsi' else [o['marka']]
        if o['dosya'] and len(markalar) != 1:
            raise CommandError('--dosya yalnızca --marka geek veya --marka baga ile kullanılabilir.')
        kuru = o['dry_run']
        self.stdout.write(self.style.WARNING('KURU ÇALIŞTIRMA — veritabanına hiçbir şey yazılmayacak.') if kuru else
                          'Aktarım başlıyor…')
        yayin_listesi = []
        for kod in markalar:
            self.stdout.write('\n' + '=' * 70 + '\n%s\n' % MARKALAR[kod]['ad'] + '=' * 70)
            satirlar = self._oku(kod, o['dosya'])
            if satirlar is None:
                continue
            try:
                with transaction.atomic():
                    self._aktar(kod, satirlar, guncelle=o['guncelle'])
                    if kuru:
                        transaction.set_rollback(True)
            except Exception as e:
                raise CommandError('%s aktarımı başarısız, hiçbir değişiklik yazılmadı: %s' % (kod, e))
            if not kuru:
                yayin_listesi.append(kod)
        if o['yayinla'] and not kuru:
            from panel.menu_yayin import csv_adresi, yayinla
            for kod in yayin_listesi:
                ok, hata = yayinla(MenuMarka.objects.get(kod=kod))
                self.stdout.write(('✔ %s yayınlandı: %s' % (kod, csv_adresi(kod))) if ok else
                                  self.style.ERROR('✘ %s yayınlanamadı: %s' % (kod, hata)))
        if kuru:
            self.stdout.write(self.style.WARNING('\nKuru çalıştırma bitti — hiçbir şey kaydedilmedi.'))

    # ------------------------------------------------------------------ okuma
    def _oku(self, kod, dosya):
        sema = MARKALAR[kod]
        try:
            if dosya:
                with open(dosya, 'rb') as f:
                    ham = f.read()
                kaynak = dosya
            else:
                kaynak = sema['csv_url']
                req = urllib.request.Request(kaynak, headers={'User-Agent': 'Mozilla/5.0 (GeekPanel menu_aktar)'})
                with urllib.request.urlopen(req, timeout=40) as r:
                    ham = r.read()
        except Exception as e:
            self.stderr.write(self.style.ERROR('%s CSV okunamadı (%s): %s' % (kod, 'dosya' if dosya else 'ağ', e)))
            return None
        metin = ham.decode('utf-8-sig', errors='replace')
        okuyucu = csv.DictReader(io.StringIO(metin))
        basliklar = [h.strip() for h in (okuyucu.fieldnames or [])]
        beklenen = sema['sutunlar']
        eksik = [c for c in beklenen if c not in basliklar]
        fazla = [c for c in basliklar if c and c not in beklenen]
        self.stdout.write('Kaynak: %s' % kaynak)
        self.stdout.write('Başlık sayısı: %d (beklenen %d)' % (len(basliklar), len(beklenen)))
        if eksik:
            self.stdout.write(self.style.WARNING('  CSV’de olmayan beklenen sütunlar: %s' % ', '.join(eksik)))
        if fazla:
            self.stdout.write(self.style.WARNING('  CSV’de olup şemada olmayan sütunlar (yok sayılır): %s' % ', '.join(fazla)))
        if 'urun_adi' not in basliklar or 'kategori_kodu' not in basliklar:
            self.stderr.write(self.style.ERROR('urun_adi / kategori_kodu sütunları yok — bu CSV beklenen şemada değil, atlandı.'))
            return None
        satirlar = []
        for ham_satir in okuyucu:
            s = {(k or '').strip(): (v or '') for k, v in ham_satir.items()}
            if not s.get('urun_adi', '').strip():          # site de bu satırları atlar
                continue
            satirlar.append(s)
        self.stdout.write('Ürün satırı: %d' % len(satirlar))
        return satirlar

    # ------------------------------------------------------------------ yazma
    def _kat_kodu(self, s, sema):
        kod = _normalize_kod(s.get('kategori_kodu'))
        kod = sema['eski_kod_yonlendirme'].get(kod, kod)
        if kod:
            return kod
        # Sitedeki geriye dönük uyumluluk: kod yoksa görünen adla eşleştir
        ad = s.get('kategori', '').strip().lower()
        for k, tr, _en in sema['kategoriler']:
            if ad in (tr.lower(), k):
                return k
        return _normalize_kod(ad)

    def _aktar(self, kod, satirlar, guncelle):
        sema = MARKALAR[kod]
        marka = MenuMarka.objects.get(kod=kod)
        sitede = set(sema['sitede_kodlar'])

        # 1) CSV'den kategori görünen adları (site gibi: kod başına en sık geçen ad)
        adlar, adlar_en = {}, {}
        for s in satirlar:
            kk = self._kat_kodu(s, sema)
            if s.get('kategori', '').strip():
                adlar.setdefault(kk, Counter())[s['kategori'].strip()] += 1
            if s.get('kategori_en', '').strip():
                adlar_en.setdefault(kk, Counter())[s['kategori_en'].strip()] += 1

        # 2) Kategoriler: sitedeki sabit kategorilerin hepsi var olsun + CSV'de geçen bilinmeyenler
        kat_olusturulan, kat_guncellenen = [], []
        siralama = OrderedDict()
        for i, (k, tr, en) in enumerate(sema['kategoriler'], 1):
            siralama[k] = (i * 10, tr, en)
        csv_kodlari = []
        for s in satirlar:
            kk = self._kat_kodu(s, sema)
            if kk not in siralama and kk not in csv_kodlari:
                csv_kodlari.append(kk)
        for j, kk in enumerate(csv_kodlari, 1):
            ad = adlar.get(kk, Counter()).most_common(1)[0][0] if kk in adlar else kk.capitalize()
            siralama[kk] = ((len(sema['kategoriler']) + j) * 10, ad, '')
        kategoriler = {}
        for kk, (sira, tr, en) in siralama.items():
            ad = adlar[kk].most_common(1)[0][0] if kk in adlar else tr
            ad_en = adlar_en[kk].most_common(1)[0][0] if kk in adlar_en else en
            kat = MenuKategori.objects.filter(marka=marka, kod=kk).first()
            if kat is None:
                kat = MenuKategori.objects.create(marka=marka, kod=kk, ad=ad, ad_en=ad_en, sira=sira)
                kat_olusturulan.append(kk)
            elif guncelle:
                if (kat.ad, kat.ad_en, kat.sira) != (ad, ad_en, sira):
                    kat.ad, kat.ad_en, kat.sira = ad, ad_en, sira
                    kat.save()
                    kat_guncellenen.append(kk)
            kategoriler[kk] = kat

        # 3) Ürünler
        olusan = guncellenen = atlanan_mevcut = 0
        gorulen = set()
        uyarilar = []
        bilinmeyen = OrderedDict()        # kategori kodu -> [ürün adları]
        kategori_sayilari = Counter()
        sirasi = Counter()
        for s in satirlar:
            ad = s['urun_adi'].strip()
            pkod = (s.get('kod') or '').strip() or tr_slug(ad)
            if not pkod:
                uyarilar.append('Kod üretilemedi, atlandı: %r' % ad)
                continue
            if pkod in gorulen:
                uyarilar.append('CSV’de tekrar eden kod, ikincisi atlandı: %s (%s)' % (pkod, ad))
                continue
            gorulen.add(pkod)
            kk = self._kat_kodu(s, sema)
            kat = kategoriler[kk]
            sitede_var = kk in sitede
            fiyat = _ondalik(s.get('fiyat'))
            if fiyat is None:
                uyarilar.append('Fiyat okunamadı → 0 yazıldı: %s (%r)' % (pkod, s.get('fiyat')))
                fiyat = Decimal('0')
            protein = _ondalik(s.get('protein'))
            kalori = None
            try:
                kalori = int(float(str(s.get('kalori') or '').replace(',', '.'))) if str(s.get('kalori') or '').strip() else None
            except ValueError:
                kalori = None
            sirasi[kk] += 1
            alanlar = {
                'kategori': kat, 'urun_adi': ad, 'urun_adi_en': s.get('urun_adi_en', '').strip(),
                'fiyat': fiyat.quantize(Decimal('0.01')),
                'aciklama': s.get('aciklama', '').strip(), 'aciklama_en': s.get('aciklama_en', '').strip(),
                'icerik': s.get('icerik', '').strip() if sema['icerik'] else '',
                'icerik_en': s.get('icerik_en', '').strip() if sema['icerik'] else '',
                'kalori': kalori, 'protein': protein.quantize(Decimal('0.1')) if protein is not None else None,
                'vegan': _dogru(s.get('vegan')),
                'sube_notu': s.get('sube_notu', '').strip(), 'sube_notu_en': s.get('sube_notu_en', '').strip(),
                'gorsel_harici': s.get('gorsel_link', '').strip()[:600],
                'sira': sirasi[kk] * 10,
            }
            for a in sema['alerjenler']:
                alanlar[a] = _dogru(s.get(a))
            mevcut = MenuUrun.objects.filter(marka=marka, kod=pkod).first()
            if mevcut is None:
                # Sitede tanımlı olmayan kategorideki ürünler zaten sitede görünmüyor:
                # veriyi kaybetmemek için içeri alınır ama menüde GÖSTERİLMEZ (aktif=False).
                MenuUrun.objects.create(marka=marka, kod=pkod, aktif=sitede_var, **alanlar)
                olusan += 1
            elif guncelle:
                for k, v in alanlar.items():
                    setattr(mevcut, k, v)
                if not sitede_var:
                    mevcut.aktif = False
                mevcut.save()
                guncellenen += 1
            else:
                atlanan_mevcut += 1
            kategori_sayilari[kk] += 1
            if not sitede_var:
                bilinmeyen.setdefault(kk, []).append('%s (%s)' % (ad, pkod))

        # 4) Rapor
        self.stdout.write('\nSonuç:')
        self.stdout.write('  Yeni ürün           : %d' % olusan)
        self.stdout.write('  Güncellenen ürün    : %d' % guncellenen)
        self.stdout.write('  Mevcut → dokunulmadı: %d%s' % (atlanan_mevcut, '' if guncelle else '  (güncellemek için --guncelle)'))
        self.stdout.write('  Yeni kategori       : %s' % (', '.join(kat_olusturulan) or '—'))
        if kat_guncellenen:
            self.stdout.write('  Güncellenen kategori: %s' % ', '.join(kat_guncellenen))
        self.stdout.write('\nCSV’deki kategori dağılımı:')
        for kk, n in kategori_sayilari.most_common():
            self.stdout.write('  %-16s %3d ürün   %s' % (kk, n, '' if kk in sitede else '← SİTEDE TANIMLI DEĞİL'))
        if bilinmeyen:
            self.stdout.write(self.style.WARNING(
                '\n⚠ QR sitesinde tanımlı olmayan kategorideki ürünler (şu an sitede GÖRÜNMÜYOR; '
                'panelde "menüde göster" kapalı olarak içeri alındı):'))
            for kk, liste in bilinmeyen.items():
                self.stdout.write(self.style.WARNING('  [%s] %d ürün:' % (kk, len(liste))))
                for x in liste:
                    self.stdout.write(self.style.WARNING('     - %s' % x))
            self.stdout.write(self.style.WARNING(
                '  Bunların görünmesi için QR sitesinin kodunda CATEGORIES dizisine ilgili kod eklenmeli '
                've ikonu tanımlanmalı; sonra panelde ürünler "menüde göster" yapılır.'))
        for u in uyarilar:
            self.stdout.write(self.style.WARNING('  uyarı: ' + u))
