from django.core.management.base import BaseCommand

# Kaynak listesi: (görünen ad, RSS besleme adresi). Hepsi Türkçe kaynak —
# yabancı bir kaynak eklenecekse başlığın Türkçe'ye çevrilmesi gerekir
# (bu komut çeviri yapmaz, bu yüzden şimdilik yalnızca Türkçe yayın yapan
# kaynaklar kullanılıyor).
HABER_KAYNAKLARI = [
    ("Sözcü - Yaşam", "https://www.sozcu.com.tr/kategori/yasam/feed/"),
    ("Hürriyet - Yaşam", "https://www.hurriyet.com.tr/rss/yasam"),
    ("NTV - Yaşam", "https://www.ntv.com.tr/yasam.rss"),
    ("Milliyet - Yaşam", "https://www.milliyet.com.tr/rss/rssnew/yasamrss.xml"),
    ("Dünya Gazetesi - Sektörler", "https://www.dunya.com/rss?xd=sektorler"),
]

HER_KAYNAKTAN_MAX = 20

# Başlıkta bu kelimelerden biri geçerse haber "Gıda/Kahve Sektörüyle İlgili"
# olarak işaretlenir ve onay ekranında öne çıkar.
GIDA_ANAHTAR_KELIMELER = [
    "kahve", "kafe", "gıda", "yemek", "yiyecek", "restoran", "mutfak", "tarif",
    "çikolata", "şeker", "bal", "süt", "inek", "çiftlik", "tarım", "çay",
    "pasta", "fırın", "ekmek", "içecek", "barista", "espresso",
]


class Command(BaseCommand):
    help = ("Türkçe kaynaklardan ilginç/ironik haber adaylarını çekip onay bekleyen "
            "listeye ekler; gıda/kahve sektörüyle ilgili başlıkları işaretler. "
            "Render'da periyodik bir cron görevi olarak çalıştırılmalı (örn. 30 dakikada bir).")

    def handle(self, *args, **opts):
        import feedparser
        from panel.models import IlginHaber

        toplam_yeni = 0
        for kaynak_ad, url in HABER_KAYNAKLARI:
            try:
                feed = feedparser.parse(url)
            except Exception as e:
                self.stderr.write("Kaynak okunamadı (%s): %s" % (kaynak_ad, e))
                continue
            if getattr(feed, 'bozo', False) and not getattr(feed, 'entries', None):
                self.stderr.write("Kaynak boş/hatalı görünüyor (%s)" % kaynak_ad)
                continue
            for entry in list(feed.entries or [])[:HER_KAYNAKTAN_MAX]:
                baslik = (getattr(entry, 'title', '') or '').strip()[:300]
                link = (getattr(entry, 'link', '') or '').strip()[:500]
                if not baslik or not link:
                    continue
                if IlginHaber.objects.filter(link=link).exists():
                    continue
                baslik_kucuk = baslik.lower()
                sektor = any(kw in baslik_kucuk for kw in GIDA_ANAHTAR_KELIMELER)
                IlginHaber.objects.create(baslik=baslik, link=link, kaynak=kaynak_ad, sektor_ilgili=sektor)
                toplam_yeni += 1
        self.stdout.write("Eklenen yeni haber adayı: %d" % toplam_yeni)
