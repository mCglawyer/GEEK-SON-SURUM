"""QR Menü — CSV üretimi ve R2'ye yayın.

Menü verisi QR sitelerine Django'dan değil, R2'deki statik CSV'den gider
(ör. medya.geekpanel.net/menu/geek.csv). Böylece panel kapalı olsa bile menü çalışır.
Her kayıt / silme / sıralama sonrası `yayinla(marka)` çağrılır.
"""
import csv
import io
import os
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from .menu_sema import MARKALAR, csv_anahtari

# Tarayıcı/CDN önbellek süresi (saniye). QR sitesi her açılışta okur; 60 sn'de
# yeni fiyatlar yansır.
CSV_CACHE_SANIYE = 60


def _bool(v):
    # QR sitesi yalnızca "TRUE" metnini doğru sayar.
    return 'TRUE' if v else 'FALSE'


def _sayi(d):
    """Decimal -> sitenin parseFloat'ının okuyacağı sade metin (nokta ayraçlı)."""
    if d is None or d == '':
        return ''
    d = Decimal(d)
    if d == d.to_integral_value():
        return str(int(d))
    return format(d.normalize(), 'f')


EK_SUTUNLAR = ['ek_alerjenler', 'ek_alerjenler_en']   # CSV'nin EN SONUNA eklenir (site sütun sırası bozulmaz)


def csv_satirlari(marka, ek=False):
    """(sütun_listesi, satır_listesi) — yalnızca aktif ürünler.
    ek=True: panelden eklenen alerjenler için iki sütun daha sona eklenir."""
    from .models import MenuUrun
    from . import menu_alerjen
    sema = MARKALAR[marka.kod]
    sutunlar = list(sema['sutunlar']) + (EK_SUTUNLAR if ek else [])
    pasif = menu_alerjen.pasif_sistem(marka)
    ekler = {a.kod: a for a in menu_alerjen.aktif_ekler(marka)}
    urunler = (MenuUrun.objects.filter(marka=marka, aktif=True)
               .select_related('kategori')
               .order_by('kategori__sira', 'kategori__id', 'sira', 'id'))
    satirlar = []
    for u in urunler:
        veri = {
            'kod': u.kod,
            'kategori_kodu': u.kategori.kod,
            'kategori': u.kategori.ad,
            'kategori_en': u.kategori.ad_en,
            'urun_adi': u.urun_adi,
            'urun_adi_en': u.urun_adi_en,
            'fiyat': _sayi(u.fiyat),
            'aciklama': u.aciklama,
            'aciklama_en': u.aciklama_en,
            'icerik': u.icerik,
            'icerik_en': u.icerik_en,
            'kalori': '' if u.kalori is None else str(u.kalori),
            'protein': _sayi(u.protein),
            'vegan': _bool(u.vegan),
            'sube_notu': u.sube_notu,
            'sube_notu_en': u.sube_notu_en,
            'gorsel_link': u.gorsel_url(),
        }
        for a in sema['alerjenler']:
            veri[a] = _bool(getattr(u, a) and a not in pasif)     # menüden kaldırılan alerjen sitede hep FALSE
        secili = [ekler[k] for k in (u.ek_alerjenler or []) if k in ekler]
        veri['ek_alerjenler'] = ', '.join(a.ad for a in secili)
        veri['ek_alerjenler_en'] = ', '.join((a.ad_en or a.ad) for a in secili)
        satirlar.append([veri.get(c, '') for c in sutunlar])
    return sutunlar, satirlar


def csv_uret(marka):
    """CSV içeriğini UTF-8 (BOM'suz) bayt olarak döndürür."""
    sutunlar, satirlar = csv_satirlari(marka, ek=True)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    w.writerow(sutunlar)
    w.writerows(satirlar)
    return buf.getvalue().encode('utf-8')


def r2_acik_mi():
    return bool(getattr(settings, 'R2_BUCKET', '') and getattr(settings, 'R2_ACCESS_KEY', '')
                and getattr(settings, 'R2_SECRET_KEY', '') and getattr(settings, 'R2_ENDPOINT_URL', ''))


def csv_adresi(marka_kod):
    """QR sitesindeki SHEET_CSV_URL'e yazılacak herkese açık adres."""
    anahtar = csv_anahtari(marka_kod)
    pub = (getattr(settings, 'R2_PUBLIC_URL', '') or '').rstrip('/')
    if r2_acik_mi() and pub:
        return '%s/%s' % (pub, anahtar)
    return '%s%s' % (settings.MEDIA_URL if settings.MEDIA_URL.startswith('/') else '/' + settings.MEDIA_URL, anahtar)


def _r2_istemci():
    import boto3
    from botocore.config import Config
    return boto3.client(
        's3',
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY,
        aws_secret_access_key=settings.R2_SECRET_KEY,
        region_name='auto',
        config=Config(signature_version='s3v4', retries={'max_attempts': 3, 'mode': 'standard'},
                      connect_timeout=8, read_timeout=15),
    )


def dosyaya_yaz(anahtar, icerik, icerik_tipi='text/csv; charset=utf-8'):
    """Dosyayı AYNI adla (üzerine yazarak) yayınlar. R2 yoksa yerel MEDIA_ROOT'a yazar."""
    if r2_acik_mi():
        _r2_istemci().put_object(
            Bucket=settings.R2_BUCKET, Key=anahtar, Body=icerik,
            ContentType=icerik_tipi,
            CacheControl='public, max-age=%d' % CSV_CACHE_SANIYE,
        )
        return
    yol = os.path.join(settings.MEDIA_ROOT, anahtar)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, 'wb') as f:
        f.write(icerik)


def yayinla(marka):
    """Markanın CSV'sini üretip yayınlar. (basarili: bool, hata_metni: str) döndürür.
    Hata durumunda istisna fırlatmaz — çağıran taraf kullanıcıya açıkça gösterir;
    veritabanı kaydı geri alınmaz."""
    try:
        icerik = csv_uret(marka)
        dosyaya_yaz(csv_anahtari(marka.kod), icerik)
    except Exception as e:  # ağ, kimlik bilgisi, izin, vb.
        hata = ('%s: %s' % (e.__class__.__name__, e))[:380]
        marka.son_yayin_hata = hata
        marka.save(update_fields=['son_yayin_hata'])
        return False, hata
    # Şube bazlı müsaitlik dosyası (yalnızca şubesi tanımlı markalar için): ürün kodu/silme değişince güncel kalsın.
    if marka.menu_subeleri.exists():
        from .menu_subeler import subeler_yayinla
        ok, hata = subeler_yayinla(marka)
        if not ok:
            hata = 'Şube listesi: ' + hata
            marka.son_yayin_hata = hata
            marka.save(update_fields=['son_yayin_hata'])
            return False, hata
    marka.son_yayin = timezone.now()
    marka.son_yayin_hata = ''
    marka.save(update_fields=['son_yayin', 'son_yayin_hata'])
    return True, ''
