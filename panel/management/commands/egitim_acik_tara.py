"""
'İnceleme bekliyor' durumunda takılı kalmış ama aslında tüm açık uçlu cevapları
zaten puanlanmış kişileri bulup sınav sonucunu kesinleştirir (aynı
_egitim_acik_sonucu_kesinlestir mantığını, tek tek tıklama beklemeden, TÜM
bekleyenler üzerinde tarar). Kimseye zarar vermez: sadece gerçekten tüm
cevapları puanlanmış olanları kesinleştirir, hâlâ gerçekten bekleyen biri
varsa ona dokunmaz.

Kullanım (Render Shell):
    python manage.py egitim_acik_tara --dry-run   (önce sadece rapor)
    python manage.py egitim_acik_tara             (gerçek kesinleştirme)
"""
from django.core.management.base import BaseCommand

from panel.models import EgitimDurum, EgitimAcikCevap
from panel.views import _egitim_ayar_getir, _bildir


class Command(BaseCommand):
    help = "'İnceleme bekliyor' durumunda takılı kalmış, tüm cevapları puanlanmış kişileri kesinleştirir."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help="Hiçbir şeyi değiştirmez, sadece kimlerin etkileneceğini raporlar.")

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        ayar = _egitim_ayar_getir()
        bekleyen_durumlar = EgitimDurum.objects.filter(inceleme_bekliyor=True).select_related('personel')

        self.stdout.write(f"'İnceleme bekliyor' durumunda toplam {bekleyen_durumlar.count()} kişi var.\n")

        kesinlesti = 0
        hala_bekliyor = 0

        for durum in bekleyen_durumlar:
            kisi = durum.personel
            if kisi is None or not durum.deneme:
                continue
            bu_deneme = EgitimAcikCevap.objects.filter(personel=kisi, deneme_no=durum.deneme)
            if not bu_deneme.exists() or bu_deneme.filter(puanlandi=False).exists():
                bekleyen_sayisi = bu_deneme.filter(puanlandi=False).count()
                self.stdout.write(f"  BEKLİYOR: {kisi.ad_soyad} — hâlâ {bekleyen_sayisi} puanlanmamış cevabı var.")
                hala_bekliyor += 1
                continue

            acik_dogru = bu_deneme.filter(dogru_mu=True).count()
            toplam_dogru = durum.son_puan + acik_dogru
            gecti_mi = toplam_dogru >= ayar.gecme_puan
            self.stdout.write(
                f"  KESİNLEŞECEK: {kisi.ad_soyad} — {toplam_dogru}/{ayar.soru_sayisi} doğru, "
                f"{'GEÇTİ' if gecti_mi else 'KALDI'}")
            kesinlesti += 1

            if dry_run:
                continue

            durum.son_puan = toplam_dogru
            durum.inceleme_bekliyor = False
            durum.gecti = gecti_mi
            durum.save()
            if gecti_mi:
                _bildir([kisi], "Eğitim sınavın değerlendirildi: %d/%d doğru — geçtin! Sözleşmeyi onaylamak için Eğitim sayfasına gir."
                        % (toplam_dogru, ayar.soru_sayisi), '/egitim/', 'egitim_sonuc')
            else:
                _bildir([kisi], "Eğitim sınavın değerlendirildi: %d/%d doğru — başarısız. Farklı sorularla tekrar deneyebilirsin."
                        % (toplam_dogru, ayar.soru_sayisi), '/egitim/', 'egitim_sonuc')

        self.stdout.write(f"\nToplam: {kesinlesti} kişi kesinleşti, {hala_bekliyor} kişi hâlâ gerçekten bekliyor.")
        if dry_run:
            self.stdout.write(self.style.WARNING("--dry-run: hiçbir şey değiştirilmedi."))
        else:
            self.stdout.write(self.style.SUCCESS("Bitti."))
