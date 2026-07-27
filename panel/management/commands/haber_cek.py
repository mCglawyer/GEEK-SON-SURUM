from django.core.management.base import BaseCommand

# Kaynak listesi: (görünen ad, RSS/Atom besleme adresi).
# Buraya istediğin kadar kaynak ekleyebilir/çıkarabilirsin — feedparser hem
# RSS 2.0 hem Atom formatını aynı şekilde okuyor, format farkı önemli değil.
HABER_KAYNAKLARI = [
    ("r/nottheonion", "https://www.reddit.com/r/nottheonion/.rss"),
    ("r/UpliftingNews", "https://www.reddit.com/r/UpliftingNews/.rss"),
]

HER_KAYNAKTAN_MAX = 15


class Command(BaseCommand):
    help = ("İronik/ilginç haber adaylarını RSS kaynaklarından çekip onay bekleyen listeye "
            "ekler. Render'da periyodik bir cron görevi olarak çalıştırılmalı (örn. 30 dakikada bir).")

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
                IlginHaber.objects.create(baslik=baslik, link=link, kaynak=kaynak_ad)
                toplam_yeni += 1
        self.stdout.write("Eklenen yeni haber adayı: %d" % toplam_yeni)
