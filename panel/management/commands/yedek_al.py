import os
import io
import gzip
import glob
import datetime

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

def yedek_dizin():
    d = os.environ.get('YEDEK_DIZIN') or os.path.join(str(settings.BASE_DIR), 'yedekler')
    os.makedirs(d, exist_ok=True)
    return d

class Command(BaseCommand):
    help = "Veritabanının tarihli (gzip) yedeğini alır ve eski yedekleri temizler."

    def add_arguments(self, parser):
        parser.add_argument('--tut', type=int, default=14,
                            help='Saklanacak yedek sayısı (varsayılan 14).')

    def handle(self, *args, **opts):
        d = yedek_dizin()
        ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        ad = f'yedek-{ts}.json.gz'
        yol = os.path.join(d, ad)

        buf = io.StringIO()
        call_command('dumpdata',
                     natural_foreign=True, natural_primary=True,
                     exclude=['contenttypes', 'auth.permission', 'admin.logentry', 'sessions'],
                     indent=2, stdout=buf)
        data = buf.getvalue().encode('utf-8')
        with gzip.open(yol, 'wb') as f:
            f.write(data)

        tut = max(1, opts['tut'])
        dosyalar = sorted(glob.glob(os.path.join(d, 'yedek-*.json.gz')))
        silinen = 0
        if len(dosyalar) > tut:
            for eski in dosyalar[:-tut]:
                try:
                    os.remove(eski)
                    silinen += 1
                except OSError:
                    pass

        self.stdout.write(self.style.SUCCESS(
            f"Yedek alındı: {ad} ({len(data) // 1024} KB). "
            f"Klasör: {d} · toplam {len(dosyalar) - silinen} yedek (silinen: {silinen})."))
