"""Ürün kataloğunu panel/sevkiyat_katalog.py içindeki KATALOG'dan yükler/günceller.
Kullanım: python manage.py katalog_yukle
Mevcut ürünler (form+ad) güncellenir, yenileri eklenir; tekrar çalıştırmak güvenlidir.
"""
from django.core.management.base import BaseCommand
from panel.models import Urun
from panel.sevkiyat_katalog import KATALOG


class Command(BaseCommand):
    help = "Sevkiyat ürün kataloğunu yükler/günceller."

    def handle(self, *args, **opts):
        eklenen = guncellenen = 0
        for sira, (form, kategori, ad, koli, birim) in enumerate(KATALOG):
            obj, created = Urun.objects.update_or_create(
                form=form, ad=ad,
                defaults={'kategori': kategori, 'koli_icerigi': koli,
                          'birim': birim, 'sira': sira, 'aktif': True},
            )
            if created:
                eklenen += 1
            else:
                guncellenen += 1
        self.stdout.write(self.style.SUCCESS(
            f"Katalog yüklendi: {eklenen} yeni, {guncellenen} güncellendi, toplam {len(KATALOG)}."))
