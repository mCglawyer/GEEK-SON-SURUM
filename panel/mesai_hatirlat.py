"""Vardiyadan veri çekip mesai QR'ı hatırlatma bildirimi.

Sabahçı 07.30–16.30, akşamcı 15.30–00.30. Her kişiye:
  1) vardiya başlangıcından 15 dk önce  "mesai QR'ınızı okutunuz" bildirimi,
  2) başlangıçtan 15 dk sonra hâlâ giriş kaydı yoksa bir kez daha.
Vardiya bitişinde (16.30 / 00.30) girişi olup çıkış QR'ı okutmamış olanlara "çıkış QR'ınızı okutunuz",
15 dk sonra hâlâ çıkış yapmamışsa bir kez daha.
Aynı bildirim aynı güne iki kez gitmez (Bildirim tablosundan kontrol edilir).
"""
import datetime

from django.utils import timezone

BASLANGIC = {'Sabahçı': datetime.time(7, 30), 'Akşamcı': datetime.time(15, 30)}
BITIS = {'Sabahçı': '16.30', 'Akşamcı': '00.30'}
ONCE_DK = 15
TEKRAR_DK = 15
PENCERE_DK = 60      # başlangıçtan bu kadar sonra artık hatırlatma yapma
TUR_ILK, TUR_TEKRAR = 'mesai_qr', 'mesai_qr2'
TUR_CIKIS, TUR_CIKIS2 = 'mesai_cikis', 'mesai_cikis2'
SURE_SA = 9          # 07.30→16.30 ve 15.30→00.30 (9 saat)
LINK = '/mesai/tara/'


def calistir(simdi=None, bildir=None):
    """Gönderilen bildirim sayısını döndürür."""
    from .models import Vardiya, VardiyaTipi, OnayDurumu, MesaiKayit, Bildirim, Rol
    if bildir is None:
        from .views import _bildir as bildir
    simdi = timezone.localtime(simdi or timezone.now())
    bugun = simdi.date()
    gonderilen = 0
    for tip, saat in BASLANGIC.items():
        bas = timezone.make_aware(datetime.datetime.combine(bugun, saat))
        ilk_an = bas - datetime.timedelta(minutes=ONCE_DK)
        if not (ilk_an <= simdi < bas + datetime.timedelta(minutes=PENCERE_DK)):
            continue
        vardiyalar = (Vardiya.objects
                      .filter(tarih=bugun, vardiya_tipi=tip, durum=OnayDurumu.ONAYLANDI,
                              personel__rol__in=[Rol.SEF, Rol.PERSONEL])
                      .select_related('personel'))
        for v in vardiyalar:
            p = v.personel
            giris_yapti = MesaiKayit.objects.filter(personel=p, giris__gte=bas - datetime.timedelta(hours=2),
                                                    giris__lt=bas + datetime.timedelta(hours=6)).exists()
            if giris_yapti:
                continue
            tekrar_zamani = simdi >= bas + datetime.timedelta(minutes=TEKRAR_DK)
            tur = TUR_TEKRAR if tekrar_zamani else TUR_ILK
            if Bildirim.objects.filter(alici=p, tur=tur, olusturma__gte=ilk_an - datetime.timedelta(minutes=1)).exists():
                continue
            if tekrar_zamani:
                msg = "Mesai QR'ınızı henüz okutmadınız. Lütfen okutunuz (%s vardiyası %02d.%02d–%s)." % (
                    tip.lower(), saat.hour, saat.minute, BITIS[tip])
            else:
                msg = "Mesai QR'ınızı okutunuz lütfen (%s vardiyası %02d.%02d–%s)." % (
                    tip.lower(), saat.hour, saat.minute, BITIS[tip])
            bildir([p], msg, LINK, tur)
            gonderilen += 1
    return gonderilen + _cikis(simdi, bildir)


def _cikis(simdi, bildir):
    """Vardiya bitişinde, çıkış QR'ı okutmamış (açık mesai kaydı olan) kişilere bildirim."""
    from .models import Vardiya, OnayDurumu, MesaiKayit, Bildirim, Rol
    gonderilen = 0
    for gun_farki in (0, 1):                       # akşamcı vardiyası ertesi gün 00.30'da biter
        gun = simdi.date() - datetime.timedelta(days=gun_farki)
        for tip, saat in BASLANGIC.items():
            bas = timezone.make_aware(datetime.datetime.combine(gun, saat))
            bitis = bas + datetime.timedelta(hours=SURE_SA)
            if not (bitis <= simdi < bitis + datetime.timedelta(minutes=PENCERE_DK)):
                continue
            vardiyalar = (Vardiya.objects
                          .filter(tarih=gun, vardiya_tipi=tip, durum=OnayDurumu.ONAYLANDI,
                                  personel__rol__in=[Rol.SEF, Rol.PERSONEL])
                          .select_related('personel'))
            for v in vardiyalar:
                p = v.personel
                acik = MesaiKayit.objects.filter(personel=p, cikis__isnull=True,
                                                 giris__gte=bas - datetime.timedelta(hours=2),
                                                 giris__lt=bitis).exists()
                if not acik:
                    continue
                tekrar = simdi >= bitis + datetime.timedelta(minutes=TEKRAR_DK)
                tur = TUR_CIKIS2 if tekrar else TUR_CIKIS
                if Bildirim.objects.filter(alici=p, tur=tur, olusturma__gte=bitis - datetime.timedelta(minutes=1)).exists():
                    continue
                msg = ("Mesainiz bitti ama çıkış QR'ını henüz okutmadınız. Lütfen okutunuz." if tekrar else
                       "Mesainiz bitti (%s). Çıkış için mesai QR'ınızı okutunuz lütfen." % BITIS[tip])
                bildir([p], msg, LINK, tur)
                gonderilen += 1
    return gonderilen
