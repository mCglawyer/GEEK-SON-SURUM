import os
import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage

from panel.models import (Sube, Personel, Vardiya, Zayi, SevkiyatTalep,
                          StokSayim, VardiyaTipi, Rol)

CALISMA = [VardiyaTipi.SABAHCI, VardiyaTipi.ARACI, VardiyaTipi.AKSAMCI]
AYLAR = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
         'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']


def rapor_dizin():
    d = os.environ.get('RAPOR_DIZIN') or os.path.join(str(settings.BASE_DIR), 'raporlar')
    os.makedirs(d, exist_ok=True)
    return d


class Command(BaseCommand):
    help = "Geçen ayın operasyon özet raporunu (PDF) oluşturur, kaydeder ve yöneticilere e-postalar."

    def add_arguments(self, parser):
        parser.add_argument('--ay', type=str, default='', help='YYYY-MM (boşsa geçen ay).')
        parser.add_argument('--force', action='store_true', help='Ayın 1’i değilse de çalıştır.')
        parser.add_argument('--mail', action='store_true', help='E-posta göndermeyi dene.')

    def handle(self, *args, **opts):
        bugun = datetime.date.today()
        if opts['ay']:
            yil, ay = map(int, opts['ay'].split('-'))
            ilk = datetime.date(yil, ay, 1)
        else:
            # geçen ay
            ilk = (bugun.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)

        if not opts['force'] and not opts['ay'] and bugun.day != 1:
            self.stdout.write("Bugün ayın 1'i değil, atlandı (--force ile zorlayabilirsiniz).")
            return

        son = (ilk.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)  # sonraki ayın 1'i
        etiket = "%s %s" % (AYLAR[ilk.month], ilk.year)

        satirlar = []
        t_cg = t_iz = t_rp = t_dv = t_zy = t_sv = 0
        for s in Sube.objects.order_by('ad'):
            vq = Vardiya.objects.filter(personel__sube=s, tarih__gte=ilk, tarih__lt=son)
            cg = vq.filter(vardiya_tipi__in=CALISMA).count()
            iz = vq.filter(vardiya_tipi=VardiyaTipi.IZINLI).count()
            rp = vq.filter(vardiya_tipi=VardiyaTipi.RAPORLU).count()
            dv = vq.filter(vardiya_tipi=VardiyaTipi.DEVAMSIZ).count()
            zy = Zayi.objects.filter(sube=s, olusturma__date__gte=ilk, olusturma__date__lt=son).count()
            sv = SevkiyatTalep.objects.filter(sube=s, olusturma__date__gte=ilk, olusturma__date__lt=son).count()
            sayim = "Evet" if StokSayim.objects.filter(sube=s, ay=ilk).exists() else "Hayır"
            satirlar.append([s.ad, cg, iz, rp, dv, zy, sv, sayim])
            t_cg += cg; t_iz += iz; t_rp += rp; t_dv += dv; t_zy += zy; t_sv += sv
        toplam = ['TOPLAM', t_cg, t_iz, t_rp, t_dv, t_zy, t_sv, '']

        from panel.aylik_rapor_pdf import aylik_rapor_bytes
        pdf = aylik_rapor_bytes(etiket, satirlar, toplam)

        d = rapor_dizin()
        ad = "rapor-%04d-%02d.pdf" % (ilk.year, ilk.month)
        yol = os.path.join(d, ad)
        with open(yol, 'wb') as f:
            f.write(pdf)
        self.stdout.write(self.style.SUCCESS("Rapor oluşturuldu: %s (%s KB)" % (ad, len(pdf) // 1024)))

        # E-posta (opsiyonel)
        if opts['mail'] or os.environ.get('RAPOR_MAIL') == '1':
            alicilar = []
            for p in Personel.objects.filter(rol__in=[Rol.GENEL_MUDUR, Rol.MUDUR, Rol.OPERATOR, Rol.YATIRIMCI]):
                e = getattr(getattr(p, 'user', None), 'email', '') or ''
                if e and e not in alicilar:
                    alicilar.append(e)
            if not getattr(settings, 'EMAIL_HOST', ''):
                self.stdout.write("E-posta ayarı yok (EMAIL_HOST), gönderilmedi.")
            elif not alicilar:
                self.stdout.write("Alıcı e-postası bulunamadı (yönetici User.email boş), gönderilmedi.")
            else:
                try:
                    msg = EmailMessage(
                        subject="Geek Panel · Aylık Operasyon Raporu (%s)" % etiket,
                        body="Ekte %s dönemine ait şube operasyon özeti yer almaktadır." % etiket,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                        to=alicilar)
                    msg.attach(ad, pdf, 'application/pdf')
                    msg.send()
                    self.stdout.write(self.style.SUCCESS("E-posta gönderildi: %s" % ", ".join(alicilar)))
                except Exception as e:
                    self.stdout.write(self.style.ERROR("E-posta gönderilemedi: %s" % e))
