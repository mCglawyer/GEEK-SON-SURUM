"""
Her sabah, sorumlu şubesi olan Bölge Müdürlerine günün özetini (izinli/raporlu
sayısı + açık sevkiyat sayısı) push bildirimi olarak gönderir. Bildirimdeki
sayı, PWA uygulama ikonunda bir rozet (badge) olarak da görünür — böylece
Bölge Müdürü uygulamayı hiç açmadan, ana ekrandaki ikona bakarak "bugün
dikkat edilmesi gereken kaç şey var" bilgisini alır.

Render Cron Job için: her gün TR saatiyle 08:00'de çalışacak şekilde
render.yaml'da UTC 05:00 olarak tanımlanmıştır.

Kullanım:
    python manage.py sabah_ozeti_gonder
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from panel.models import Personel, Rol, Vardiya, VardiyaTipi, SevkiyatTalep, SevkiyatDurumu
from panel.views import _bildir


class Command(BaseCommand):
    help = "Bölge Müdürlerine günün özetini push bildirimi + uygulama rozeti olarak gönderir."

    def handle(self, *args, **options):
        bugun = timezone.localdate()
        gonderilen = 0

        muduerler = Personel.objects.filter(rol=Rol.MUDUR).prefetch_related('sorumlu_subeler')
        for md in muduerler:
            hesap_ids = list(md.sorumlu_subeler.values_list('id', flat=True))
            if not hesap_ids:
                continue

            v_today = Vardiya.objects.filter(tarih=bugun, personel__sube_id__in=hesap_ids)
            izinli = v_today.filter(vardiya_tipi__in=[VardiyaTipi.IZINLI, VardiyaTipi.YILLIK_IZIN]).count()
            raporlu = v_today.filter(vardiya_tipi=VardiyaTipi.RAPORLU).count()
            acik_sevkiyat = SevkiyatTalep.objects.filter(
                sube_id__in=hesap_ids,
                durum__in=[SevkiyatDurumu.TALEP, SevkiyatDurumu.SEVKIYATTA, SevkiyatDurumu.ONAY_BEKLIYOR]
            ).count()

            toplam = izinli + raporlu + acik_sevkiyat
            if toplam == 0:
                continue

            mesaj = "Bugün: %d izinli, %d raporlu, %d açık sevkiyat siparişi var." % (izinli, raporlu, acik_sevkiyat)
            _bildir([md], mesaj, '/gosterge/', 'sabah_ozeti', sayi=toplam)
            gonderilen += 1

        self.stdout.write(self.style.SUCCESS("Bitti: %d Bölge Müdürü'ne sabah özeti gönderildi." % gonderilen))
