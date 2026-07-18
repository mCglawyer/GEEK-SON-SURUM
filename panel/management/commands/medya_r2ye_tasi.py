"""
Yerel diskteki (MEDIA_ROOT) tüm medya dosyalarını Cloudflare R2'ye, aynı göreli
yol yapısıyla yükler. Aynı göreli yol kullanıldığı için veritabanındaki mevcut
FileField/ImageField kayıtları HİÇ değişmeden R2'deki dosyaları doğru bulur —
bu komuttan sonra ekstra bir veri taşıma/güncelleme gerekmez.

Bu komutu PythonAnywhere'de (dosyaların hâlâ yerel diskte olduğu yerde) çalıştırın.

Kullanım (PythonAnywhere bash, R2 bilgilerini geçici olarak ortam değişkeni verin):
    export R2_BUCKET=geek-panel-medya
    export R2_ACCESS_KEY=xxxx
    export R2_SECRET_KEY=xxxx
    export R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com

    python manage.py medya_r2ye_tasi --dry-run   (önce sadece rapor, hiçbir şey yüklemez)
    python manage.py medya_r2ye_tasi             (gerçek yükleme)
"""
import os
import mimetypes

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "MEDIA_ROOT altındaki tüm dosyaları Cloudflare R2'ye (aynı göreli yol ile) yükler."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="Hiçbir şey yüklemez, sadece kaç dosya/kaç MB olduğunu raporlar.")

    def handle(self, *args, **options):
        bucket = os.environ.get('R2_BUCKET')
        access_key = os.environ.get('R2_ACCESS_KEY')
        secret_key = os.environ.get('R2_SECRET_KEY')
        endpoint = os.environ.get('R2_ENDPOINT_URL')

        if not all([bucket, access_key, secret_key, endpoint]):
            raise CommandError(
                "R2_BUCKET, R2_ACCESS_KEY, R2_SECRET_KEY, R2_ENDPOINT_URL ortam "
                "değişkenlerinin hepsi tanımlı olmalı (export ile geçici verebilirsiniz).")

        try:
            import boto3
        except ImportError:
            raise CommandError("boto3 kurulu değil. Önce: pip install -r requirements.txt")

        media_root = str(settings.MEDIA_ROOT)
        if not os.path.isdir(media_root):
            self.stdout.write(self.style.WARNING(f"Medya klasörü bulunamadı: {media_root}"))
            return

        s3 = boto3.client(
            's3', endpoint_url=endpoint,
            aws_access_key_id=access_key, aws_secret_access_key=secret_key,
            region_name='auto',
        )

        dosyalar = []
        for kok, _dizinler, isimler in os.walk(media_root):
            for ad in isimler:
                tam_yol = os.path.join(kok, ad)
                goreli_yol = os.path.relpath(tam_yol, media_root).replace(os.sep, '/')
                dosyalar.append((tam_yol, goreli_yol))

        if not dosyalar:
            self.stdout.write("Yüklenecek dosya bulunamadı.")
            return

        toplam_mb = sum(os.path.getsize(t) for t, _ in dosyalar) / (1024 * 1024)
        self.stdout.write(f"{len(dosyalar)} dosya bulundu, toplam {toplam_mb:.1f} MB.")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("--dry-run: hiçbir dosya yüklenmedi."))
            return

        basarili, hatali = 0, 0
        for i, (tam_yol, goreli_yol) in enumerate(dosyalar, 1):
            icerik_turu, _ = mimetypes.guess_type(tam_yol)
            try:
                extra = {'ContentType': icerik_turu} if icerik_turu else {}
                s3.upload_file(tam_yol, bucket, goreli_yol, ExtraArgs=extra)
                basarili += 1
            except Exception as e:
                hatali += 1
                self.stdout.write(self.style.ERROR(f"[{i}/{len(dosyalar)}] HATA {goreli_yol}: {e}"))
                continue
            if i % 25 == 0 or i == len(dosyalar):
                self.stdout.write(f"[{i}/{len(dosyalar)}] yüklendi...")

        self.stdout.write(self.style.SUCCESS(
            f"\nBitti: {basarili} dosya yüklendi, {hatali} hata. "
            f"Şimdi Render tarafında R2_* ortam değişkenlerini ayarlayıp "
            f"deploy edebilirsiniz."))
