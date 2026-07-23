"""
Personel ve Şef rolündeki herkesin eğitim sınav durumunu (tamamlandı/geçti/puan/deneme
sayısı, açık uçlu cevaplar dahil) tamamen sıfırlar. Sıfırlanan kişiler bir sonraki
/egitim/ ziyaretinde sıfırdan (hiç sınava girmemiş gibi) başlar.

Not: Bu, EgitimSoru (soru havuzu) veya EgitimAyar (soru sayısı/süre/geçme puanı)
ayarlarına DOKUNMAZ — sadece kişilerin sınav SONUÇLARINI sıfırlar.

Kullanım (Render Shell veya PythonAnywhere bash):
    python manage.py egitim_sifirla --dry-run   (önce sadece kaç kişi etkilenecek, rapor)
    python manage.py egitim_sifirla             (gerçek sıfırlama)
"""
from django.core.management.base import BaseCommand

from panel.models import Personel, EgitimDurum, EgitimAcikCevap, Rol


class Command(BaseCommand):
    help = "Personel/Şef rolündeki herkesin eğitim sınav durumunu sıfırlar (herkes tekrar sınava girer)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="Hiçbir şeyi sıfırlamaz, sadece kaç kişinin etkileneceğini raporlar.")

    def handle(self, *args, **options):
        hedef_kisiler = Personel.objects.filter(rol__in=[Rol.PERSONEL, Rol.SEF])
        durumlar = EgitimDurum.objects.filter(personel__in=hedef_kisiler, deneme__gt=0)
        acik_cevaplar = EgitimAcikCevap.objects.filter(personel__in=hedef_kisiler)

        etkilenen_kisi = durumlar.count()
        acik_cevap_sayisi = acik_cevaplar.count()

        self.stdout.write(f"Toplam Personel/Şef: {hedef_kisiler.count()}")
        self.stdout.write(f"Daha önce sınava girmiş (sıfırlanacak) kişi sayısı: {etkilenen_kisi}")
        self.stdout.write(f"Silinecek açık uçlu cevap sayısı: {acik_cevap_sayisi}")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("--dry-run: hiçbir şey sıfırlanmadı."))
            return

        acik_cevaplar.delete()
        guncellendi = durumlar.update(
            tamamlandi=False, gecti=False, inceleme_bekliyor=False,
            son_puan=0, deneme=0, son_sorular='', son_cevaplar='',
            sozlesme_onayli=False,
        )

        self.stdout.write(self.style.SUCCESS(
            f"\nBitti: {guncellendi} kişinin sınav durumu sıfırlandı. "
            f"Herkes /egitim/ sayfasına girince sıfırdan sınava başlayabilir."))
