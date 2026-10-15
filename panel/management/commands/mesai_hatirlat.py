from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Vardiyadaki şef/personele mesai QR okutma hatırlatması gönderir (mola_kontrol işçisi bunu zaten dakikada bir çağırır)."

    def handle(self, *args, **opts):
        from panel.mesai_hatirlat import calistir
        self.stdout.write("%d hatırlatma gönderildi." % calistir())
