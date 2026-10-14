"""Mola kuralları — QR okutunca başlar, tekrar okutunca biter.

Akış
  * Şubedeki QR okutulur  -> mola o an başlar (buton yok).
  * Dönüşte QR tekrar okutulur -> mola o an biter (buton yok).
  * Gün içinde istenen kadar mola yapılabilir; gün sonunda toplam süre + hangi saatlerde çıkıldığı görünür.

Kurallar (tek yerde; değiştirmek için yalnızca buradaki sabitler):
  MOLA_GUNLUK_LIMIT_DK   günlük toplam mola hakkı. Aşılırsa raporlarda "Aşım" görünür.
  MOLA_OTO_KAPAT_DK      dönüş QR'ı okutulmayan mola bu süreden sonra kendiliğinden kapanır
                         (kayıtta "Otomatik kapatıldı" notu olur, süre olarak bu üst sınır sayılır).
  MOLA_CIFT_OKUTMA_SN    başlama/bitişten sonra bu kadar saniye içindeki ikinci okutma yok sayılır
                         (kameranın iki kez okuması, yanlışlıkla tekrar tutma).

Veritabanı alanı eklenmedi: otomatik kapanma `manuel_not` metniyle işaretlenir.
"""
import datetime

from django.db import transaction
from django.utils import timezone

from .models import MolaOturum, Personel

MOLA_GUNLUK_LIMIT_DK = 60
MOLA_OTO_KAPAT_DK = 120
MOLA_CIFT_OKUTMA_SN = 60
OTO_KAPANDI_NOTU = 'Otomatik kapatıldı (dönüş QR’ı okutulmadı)'


def dakika(m, simdi=None):
    """Bir mola kaydının kullanılan dakikası (bitmemişse şimdiye kadar geçen)."""
    if m.bitis is not None:
        if m.kullanilan_dk is not None:
            return m.kullanilan_dk
        return max(0, int((m.bitis - m.baslangic).total_seconds() // 60))
    simdi = simdi or timezone.now()
    return max(0, int((simdi - m.baslangic).total_seconds() // 60))


def oto_kapandi_mi(m):
    return (m.manuel_not or '').startswith('Otomatik kapatıldı')


def gun_araligi(tarih):
    tz = timezone.get_current_timezone()
    bas = timezone.make_aware(datetime.datetime.combine(tarih, datetime.time.min), tz)
    return bas, bas + datetime.timedelta(days=1)


def gunun_molalari(personel, tarih=None):
    """O günün (yerel tarih) tüm molaları, en eskiden yeniye."""
    tarih = tarih or timezone.localdate()
    bas, bit = gun_araligi(tarih)
    return list(MolaOturum.objects.filter(personel=personel, baslangic__gte=bas, baslangic__lt=bit)
                .select_related('sube').order_by('baslangic'))


def gunluk_kullanim(personel, tarih=None, simdi=None):
    """O gün biten + sürmekte olan tüm molaların toplam dakikası."""
    return sum(dakika(m, simdi) for m in gunun_molalari(personel, tarih))


def hak_dk(kullanilan):
    return max(0, MOLA_GUNLUK_LIMIT_DK - kullanilan)


def oto_kapat(m, simdi=None):
    """Unutulan molayı kapat: bitiş = başlangıç + üst sınır."""
    m.bitis = m.baslangic + datetime.timedelta(minutes=MOLA_OTO_KAPAT_DK)
    if simdi is not None and m.bitis > simdi:
        m.bitis = simdi
    m.kullanilan_dk = max(0, int((m.bitis - m.baslangic).total_seconds() // 60))
    if not m.manuel_not:
        m.manuel_not = OTO_KAPANDI_NOTU
    m.save(update_fields=['bitis', 'kullanilan_dk', 'manuel_not'])
    return m


def eskileri_kapat(simdi=None, personel=None):
    """Süresi aşılmış açık molaları kapatır; kapatılan sayısını döner."""
    simdi = simdi or timezone.now()
    sinir = simdi - datetime.timedelta(minutes=MOLA_OTO_KAPAT_DK)
    qs = MolaOturum.objects.filter(bitis__isnull=True, baslangic__lte=sinir)
    if personel is not None:
        qs = qs.filter(personel=personel)
    sayac = 0
    for m in qs:
        oto_kapat(m, simdi)
        sayac += 1
    return sayac


def okut(personel, sube, simdi=None):
    """QR okutuldu: duruma göre molayı başlatır ya da bitirir.

    Dönen sözlük: eylem ('basladi' | 'bitti' | 'zaten_basladi' | 'az_once_bitti'),
    mola (ilgili kayıt), oto (bu okutmada unutulan eski mola kapatıldı mı).
    Aynı kişinin eşzamanlı iki isteği kayıt satırı kilidiyle sıraya girer (çift mola açılmaz).
    """
    simdi = simdi or timezone.now()
    with transaction.atomic():
        Personel.objects.select_for_update().get(pk=personel.pk)
        oto = False
        aktif = (MolaOturum.objects.filter(personel=personel, bitis__isnull=True)
                 .order_by('-baslangic').first())
        if aktif is not None and (simdi - aktif.baslangic).total_seconds() > MOLA_OTO_KAPAT_DK * 60:
            oto_kapat(aktif, simdi)
            oto, aktif = True, None
        if aktif is not None:
            if (simdi - aktif.baslangic).total_seconds() < MOLA_CIFT_OKUTMA_SN:
                return {'eylem': 'zaten_basladi', 'mola': aktif, 'oto': oto}
            aktif.bitis = simdi
            aktif.kullanilan_dk = max(0, int((simdi - aktif.baslangic).total_seconds() // 60))
            aktif.save(update_fields=['bitis', 'kullanilan_dk'])
            return {'eylem': 'bitti', 'mola': aktif, 'oto': oto}
        son = (MolaOturum.objects.filter(personel=personel, bitis__isnull=False)
               .order_by('-bitis').first())
        if son is not None and (simdi - son.bitis).total_seconds() < MOLA_CIFT_OKUTMA_SN:
            return {'eylem': 'az_once_bitti', 'mola': son, 'oto': oto}
        kullanilan = gunluk_kullanim(personel, timezone.localtime(simdi).date(), simdi)
        yeni = MolaOturum.objects.create(personel=personel, sube=sube, sure_dk=hak_dk(kullanilan),
                                         sure_secildi=True, baslangic=simdi)
        return {'eylem': 'basladi', 'mola': yeni, 'oto': oto}


def gunluk_gruplar(kayitlar):
    """Biten mola kayıtları -> (gün, kişi) bazında toplam ve çıkış saatleri.

    Dönen liste yeni günden eskiye; her öğe: tarih, ad, sube, molalar[{giris, cikis, dk, oto, manuel}],
    toplam_dk, limit, asti, adet.
    """
    gruplar = {}
    for m in kayitlar:
        giris = timezone.localtime(m.baslangic)
        anahtar = (giris.date(), m.personel_id)
        g = gruplar.get(anahtar)
        if g is None:
            g = gruplar[anahtar] = {
                'tarih': giris.date(), 'ad': m.personel.ad_soyad if m.personel_id else '—',
                'sube': m.sube.ad if m.sube_id else '—', 'molalar': [], 'toplam_dk': 0}
        dk = dakika(m)
        g['molalar'].append({'giris': giris, 'cikis': timezone.localtime(m.bitis), 'dk': dk,
                             'oto': oto_kapandi_mi(m), 'manuel': m.manuel_mi})
        g['toplam_dk'] += dk
    liste = sorted(gruplar.values(), key=lambda x: (x['tarih'], x['ad'].casefold()), reverse=False)
    liste.sort(key=lambda x: x['tarih'], reverse=True)
    for g in liste:
        g['molalar'].sort(key=lambda x: x['giris'])
        g['adet'] = len(g['molalar'])
        g['limit'] = MOLA_GUNLUK_LIMIT_DK
        g['asti'] = g['toplam_dk'] > MOLA_GUNLUK_LIMIT_DK
        g['oto'] = any(x['oto'] for x in g['molalar'])
    return liste
