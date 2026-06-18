from django.core.management.base import BaseCommand

from panel.kahve_sorulari import SORULAR
from panel.models import KahveSoru


class Command(BaseCommand):
    help = "Kahve soru bankasını (kahve_sorulari.py) veritabanına yükler."

    def handle(self, *args, **opts):
        eklenen = guncellenen = 0
        gelen = set()
        for kat, metin, a, b, c, d, dogru in SORULAR:
            gelen.add(metin)
            obj, created = KahveSoru.objects.update_or_create(
                metin=metin,
                defaults={'kategori': kat, 'sik_a': a, 'sik_b': b, 'sik_c': c,
                          'sik_d': d, 'dogru': dogru, 'aktif': True},
            )
            eklenen += 1 if created else 0
            guncellenen += 0 if created else 1
        # Bankadan çıkarılanları pasifleştir
        pasif = 0
        for s in KahveSoru.objects.filter(aktif=True):
            if s.metin not in gelen:
                s.aktif = False
                s.save(update_fields=['aktif'])
                pasif += 1
        self.stdout.write(self.style.SUCCESS(
            f"Soru bankası yüklendi: {eklenen} yeni, {guncellenen} güncellendi, "
            f"{pasif} pasifleştirildi, toplam {len(SORULAR)}."))
