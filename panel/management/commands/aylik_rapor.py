import os
import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage

from panel.models import (Sube, Personel, Vardiya, MolaOturum, SevkiyatTalep,
                          StokSayim, VardiyaTipi, Rol)

CALISMA = [VardiyaTipi.SABAHCI, VardiyaTipi.ARACI, VardiyaTipi.AKSAMCI]
AYLAR = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
         'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']

def rapor_dizin():
    d = os.environ.get('RAPOR_DIZIN') or os.path.join(str(settings.BASE_DIR), 'raporlar')
    os.makedirs(d, exist_ok=True)
    return d

class Command(BaseCommand):
    help = "Geçen ayın detaylı operasyon raporunu (şube şube, personel bazında) PDF üretir, kaydeder, e-postalar."

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
            ilk = (bugun.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)

        if not opts['force'] and not opts['ay'] and bugun.day != 1:
            self.stdout.write("Bugün ayın 1'i değil, atlandı (--force ile zorlayabilirsiniz).")
            return

        son = (ilk.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        etiket = "%s %s" % (AYLAR[ilk.month], ilk.year)

        subeler_veri = []
        g_cg = g_iz = g_rp = g_dv = g_sv = 0
        for s in Sube.objects.order_by('ad'):
            p_rows = []
            tc = ti = tr = td = tms = tmd = 0
            for p in Personel.objects.filter(sube=s, rol__in=[Rol.PERSONEL, Rol.SEF]).order_by('ad_soyad'):
                vq = Vardiya.objects.filter(personel=p, tarih__gte=ilk, tarih__lt=son)
                cg = vq.filter(vardiya_tipi__in=CALISMA).count()
                iz = vq.filter(vardiya_tipi=VardiyaTipi.IZINLI).count()
                rp = vq.filter(vardiya_tipi=VardiyaTipi.RAPORLU).count()
                dv = vq.filter(vardiya_tipi=VardiyaTipi.DEVAMSIZ).count()
                molalar = list(MolaOturum.objects.filter(
                    personel=p, baslangic__date__gte=ilk, baslangic__date__lt=son, bitis__isnull=False))
                ms = len(molalar)
                md = sum(
                    (m.kullanilan_dk if m.kullanilan_dk is not None
                     else max(0, int((m.bitis - m.baslangic).total_seconds() // 60)))
                    for m in molalar)
                p_rows.append({'ad': p.ad_soyad, 'calisan': cg, 'izin': iz, 'rapor': rp,
                               'devamsiz': dv, 'mola_say': ms, 'mola_dk': md})
                tc += cg; ti += iz; tr += rp; td += dv; tms += ms; tmd += md
            sv = SevkiyatTalep.objects.filter(sube=s, olusturma__date__gte=ilk, olusturma__date__lt=son).count()
            sayim = "Evet" if StokSayim.objects.filter(sube=s, ay=ilk).exists() else "Hayır"
            subeler_veri.append({
                'ad': s.ad,
                'ozet': {'sevkiyat': sv, 'sayim': sayim},
                'personeller': p_rows,
                'toplam': {'calisan': tc, 'izin': ti, 'rapor': tr, 'devamsiz': td,
                           'mola_say': tms, 'mola_dk': tmd},
            })
            g_cg += tc; g_iz += ti; g_rp += tr; g_dv += td; g_sv += sv
        genel = {'calisan': g_cg, 'izin': g_iz, 'rapor': g_rp, 'devamsiz': g_dv,
                 'sevkiyat': g_sv}

        from panel.aylik_rapor_pdf import aylik_rapor_bytes
        pdf = aylik_rapor_bytes(etiket, subeler_veri, genel)

        d = rapor_dizin()
        ad = "rapor-%04d-%02d.pdf" % (ilk.year, ilk.month)
        with open(os.path.join(d, ad), 'wb') as f:
            f.write(pdf)
        self.stdout.write(self.style.SUCCESS("Rapor oluşturuldu: %s (%s KB)" % (ad, len(pdf) // 1024)))

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
                        body="Ekte %s dönemine ait şube/personel operasyon detayı yer almaktadır." % etiket,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None), to=alicilar)
                    msg.attach(ad, pdf, 'application/pdf')
                    msg.send()
                    self.stdout.write(self.style.SUCCESS("E-posta gönderildi: %s" % ", ".join(alicilar)))
                except Exception as e:
                    self.stdout.write(self.style.ERROR("E-posta gönderilemedi: %s" % e))
