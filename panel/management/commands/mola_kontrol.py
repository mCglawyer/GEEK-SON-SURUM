import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Aktif molaları kontrol eder; bitişe 5 dk kala 'süren doluyor' bildirimi atar. Always-On task olarak sürekli çalıştırın."

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Tek sefer çalış, döngü kurma (test için).')
        parser.add_argument('--aralik', type=int, default=60, help='Kontrol aralığı (saniye).')

    def handle(self, *args, **opts):
        once = opts.get('once')
        aralik = opts.get('aralik') or 60
        self.stdout.write("mola_kontrol başladı (aralık=%ss)." % aralik)
        while True:
            try:
                self._kontrol()
            except Exception as e:
                self.stderr.write("mola_kontrol hata: %s" % e)
            if once:
                break
            time.sleep(aralik)

    def _kontrol(self):
        from panel.models import MolaOturum, Personel, Rol
        from panel.views import _bildir
        now = timezone.now()
        aktifler = list(MolaOturum.objects.filter(bitis__isnull=True, uyarildi=False).select_related('personel', 'sube'))
        for m in aktifler:
            try:
                bitecek = m.baslangic + timedelta(minutes=m.sure_dk)
                kalan = (bitecek - now).total_seconds()
                if kalan <= 0:
                    # süre dolmuş; tekrar denenmesin
                    m.uyarildi = True
                    m.save(update_fields=['uyarildi'])
                elif kalan <= 300:
                    alicilar = [m.personel]
                    if m.sube_id:
                        alicilar += list(Personel.objects.filter(sube_id=m.sube_id, rol=Rol.SEF))
                    _bildir(alicilar, "%s için molanın bitmesine 5 dakika kaldı." % m.personel.ad_soyad,
                            '/mola/tara/', 'mola')
                    m.uyarildi = True
                    m.save(update_fields=['uyarildi'])
            except Exception as e:
                self.stderr.write("oturum %s hata: %s" % (getattr(m, 'id', '?'), e))
