from django.core.management.base import BaseCommand
from panel.models import StokUrun
from panel.stok_katalog import STOK_KATALOG

class Command(BaseCommand):
    help = "Gömülü stok sayım kataloğunu (stok_katalog.py) StokUrun tablosuna yükler/günceller."

    def handle(self, *args, **opts):
        eklendi = guncellendi = 0
        gelen_adlar = set()
        for kategori, ad, kapali, acik, sira in STOK_KATALOG:
            gelen_adlar.add(ad)
            obj, created = StokUrun.objects.update_or_create(
                ad=ad,
                defaults={'kategori': kategori, 'kapali_icerik': kapali,
                          'acik_carpan': acik, 'sira': sira, 'aktif': True},
            )
            if created:
                eklendi += 1
            else:
                guncellendi += 1

        pasif = StokUrun.objects.filter(aktif=True).exclude(ad__in=gelen_adlar).update(aktif=False)
        self.stdout.write(self.style.SUCCESS(
            f"Stok kataloğu yüklendi: {eklendi} yeni, {guncellendi} güncellendi, {pasif} pasifleştirildi. "
            f"Toplam aktif: {StokUrun.objects.filter(aktif=True).count()}"))
