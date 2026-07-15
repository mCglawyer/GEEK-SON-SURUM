"""
Zaten yüklenmiş olan Eğitim dokümanlarındaki (Reçete/Oryantasyon) PDF dosyalarını
toplu olarak sıkıştırır. Yeni yüklenen dosyalar zaten otomatik sıkıştırılıyor
(panel/views.py -> egitim_yonetim -> _pdf_sikistir); bu komut sadece GEÇMİŞTE
yüklenmiş dosyalar için tek seferlik bir bakım işlemidir.

Kullanım (PythonAnywhere bash):
    python manage.py egitim_pdf_sikistir
    python manage.py egitim_pdf_sikistir --dry-run   (sadece rapor, dosyaları değiştirmez)
"""
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile

from panel.models import EgitimDokuman
from panel.views import _pdf_sikistir


class Command(BaseCommand):
    help = "Mevcut Eğitim PDF dokümanlarını sıkıştırır (görselleri küçültüp yeniden kodlar)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="Dosyaları değiştirmeden sadece ne kadar küçüleceğini raporlar.")

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        pdfler = [d for d in EgitimDokuman.objects.all() if (d.dosya.name or '').lower().endswith('.pdf')]
        if not pdfler:
            self.stdout.write("Sıkıştırılacak PDF dokümanı bulunamadı.")
            return

        toplam_once = 0
        toplam_sonra = 0
        for d in pdfler:
            try:
                d.dosya.open('rb')
                orijinal = d.dosya.read()
                d.dosya.close()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"[atlandı] {d.baslik}: dosya okunamadı ({e})"))
                continue

            once_mb = len(orijinal) / (1024 * 1024)
            sikisik = _pdf_sikistir(orijinal)
            sonra_mb = len(sikisik) / (1024 * 1024)
            toplam_once += once_mb
            toplam_sonra += sonra_mb

            if len(sikisik) < len(orijinal):
                oran = round(100 - (len(sikisik) / len(orijinal) * 100))
                self.stdout.write(f"{d.baslik}: {once_mb:.1f} MB -> {sonra_mb:.1f} MB (%{oran} küçüldü)")
                if not dry_run:
                    ad = d.dosya.name.rsplit('/', 1)[-1]
                    d.dosya.delete(save=False)
                    d.dosya.save(ad, ContentFile(sikisik), save=True)
            else:
                self.stdout.write(f"{d.baslik}: zaten optimize (değişiklik yok)")

        self.stdout.write(self.style.SUCCESS(
            f"\nToplam: {toplam_once:.1f} MB -> {toplam_sonra:.1f} MB"
            + (" (dry-run, dosyalar değiştirilmedi)" if dry_run else "")))
