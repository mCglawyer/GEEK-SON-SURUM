from django.core.management.base import BaseCommand
from django.utils import timezone

from panel.models import Personel, Rol, GSosyalGonderi, DogumGunuKutlama, Bildirim


class Command(BaseCommand):
    help = "Bugün doğum günü olan personel için Geek Crew'da kutlama paylaşımı oluşturur. Günde bir kez, PythonAnywhere Scheduled Tasks ile çalıştırılmalıdır."

    def handle(self, *args, **options):
        bugun = timezone.localdate()
        operator = Personel.objects.filter(rol=Rol.OPERATOR).order_by('id').first()
        if operator is None:
            operator = Personel.objects.filter(rol=Rol.GENEL_MUDUR).order_by('id').first()

        adaylar = Personel.objects.filter(
            dogum_tarihi__month=bugun.month, dogum_tarihi__day=bugun.day)

        yeni = 0
        for kisi in adaylar:
            if DogumGunuKutlama.objects.filter(personel=kisi, tarih=bugun).exists():
                continue
            DogumGunuKutlama.objects.create(personel=kisi, tarih=bugun)
            if operator is None:
                continue
            metin = "🎉 Bugün %s'in doğum günü! Ekip olarak kendisine mutlu, sağlıklı bir yaş diliyoruz. 🎂" % kisi.ad_soyad
            GSosyalGonderi.objects.create(yazan=operator, yazan_ad=operator.ad_soyad, metin=metin)
            Bildirim.objects.create(alici=kisi, mesaj="İyi ki doğdun %s! 🎉" % kisi.ad_soyad,
                                    link='/g-sosyal/', tur='dogumgunu')
            yeni += 1

        self.stdout.write(self.style.SUCCESS("Doğum günü kontrolü tamam. %d kutlama paylaşıldı." % yeni))
