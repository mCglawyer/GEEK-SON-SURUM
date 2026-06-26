from django.core.management.base import BaseCommand
from panel.models import Urun
from panel.sevkiyat_katalog import KATALOG

class Command(BaseCommand):
    help = "Sevkiyat ürün kataloğunu yükler/günceller."

    def handle(self, *args, **opts):
        eklenen = guncellenen = 0
        gelen = set()
        for sira, (form, kategori, ad, koli, birim) in enumerate(KATALOG):
            gelen.add((form, ad))
            obj, created = Urun.objects.update_or_create(
                form=form, ad=ad,
                defaults={'kategori': kategori, 'koli_icerigi': koli,
                          'birim': birim, 'sira': sira, 'aktif': True},
            )
            if created:
                eklenen += 1
            else:
                guncellenen += 1

        pasif = 0
        for u in Urun.objects.filter(aktif=True):
            if (u.form, u.ad) not in gelen:
                u.aktif = False
                u.save(update_fields=['aktif'])
                pasif += 1
        self.stdout.write(self.style.SUCCESS(
            f"Katalog yüklendi: {eklenen} yeni, {guncellenen} güncellendi, {pasif} pasifleştirildi, "
            f"toplam {len(KATALOG)}."))
