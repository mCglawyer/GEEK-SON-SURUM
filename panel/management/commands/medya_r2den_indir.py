"""
R2'deki dosyaları, yerel diskte (MEDIA_ROOT) YOKSA indirir. Zaten yerel diskte
olanlara dokunmaz. Bu, R2'den yerel depolamaya GERİ DÖNÜŞ yaparken, sadece
R2'ye yüklenmiş (yerel diskte hiç var olmamış) en yeni dosyaların kaybolmamasını
sağlamak için kullanılır.

Kullanım (PythonAnywhere bash, R2 bilgilerini geçici olarak ortam değişkeni verin):
    export R2_BUCKET=geek-panel-medya
    export R2_ACCESS_KEY=xxxx
    export R2_SECRET_KEY=xxxx
    export R2_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com

    python manage.py medya_r2den_indir --dry-run   (önce sadece rapor)
    python manage.py medya_r2den_indir             (gerçek indirme)
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "R2'de olup yerel diskte olmayan dosyaları MEDIA_ROOT'a indirir."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="Hiçbir şey indirmez, sadece kaç dosya eksik olduğunu raporlar.")

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
        s3 = boto3.client(
            's3', endpoint_url=endpoint,
            aws_access_key_id=access_key, aws_secret_access_key=secret_key,
            region_name='auto',
        )

        eksik = []
        paginator = s3.get_paginator('list_objects_v2')
        for sayfa in paginator.paginate(Bucket=bucket):
            for obj in sayfa.get('Contents', []):
                anahtar = obj['Key']
                yerel_yol = os.path.join(media_root, anahtar)
                if not os.path.exists(yerel_yol):
                    eksik.append(anahtar)

        if not eksik:
            self.stdout.write(self.style.SUCCESS("Yerel diskte eksik dosya yok, hepsi zaten mevcut."))
            return

        self.stdout.write(f"{len(eksik)} dosya yerel diskte eksik.")
        if options['dry_run']:
            for anahtar in eksik:
                self.stdout.write(f"  eksik: {anahtar}")
            self.stdout.write(self.style.WARNING("--dry-run: hiçbir dosya indirilmedi."))
            return

        basarili, hatali = 0, 0
        for anahtar in eksik:
            yerel_yol = os.path.join(media_root, anahtar)
            os.makedirs(os.path.dirname(yerel_yol), exist_ok=True)
            try:
                s3.download_file(bucket, anahtar, yerel_yol)
                basarili += 1
                self.stdout.write(f"indirildi: {anahtar}")
            except Exception as e:
                hatali += 1
                self.stdout.write(self.style.ERROR(f"HATA {anahtar}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"\nBitti: {basarili} dosya indirildi, {hatali} hata."))
