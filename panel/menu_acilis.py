"""QR Menü — açılış (kampanya) görseli yönetimi.

Müşteri QR sitesini açınca ekrana gelen görselleri panelden yönetiriz. QR siteleri panele değil, R2'deki statik
JSON'a bakar (ör. medya.geekpanel.net/menu/geek-acilis.json); panel kapalı olsa bile site çalışır.
Her kayıt sonrası JSON yeniden yayınlanır. Tarih aralıkları JSON'da gider, müşteri cihazında uygulanır
(böylece kampanya bitiş günü yeniden yayın gerekmez).
"""
import datetime
import hashlib
import json
import uuid
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile
from django.db.models import Max
from django.shortcuts import redirect, render
from django.utils import timezone

from .menu_sema import MARKALAR
from .menu_yayin import dosyaya_yaz, r2_acik_mi
from .models import MenuAcilisGorsel

MAX_GORSEL = 8
MAX_DOSYA_MB = 12
MAX_KENAR = 1600
SURE_MIN, SURE_MAX = 2, 15


def acilis_anahtari(marka_kod):
    return 'menu/%s-acilis.json' % marka_kod


def acilis_adresi(marka_kod):
    """QR sitesindeki ACILIS_JSON_URL'e yazılacak herkese açık adres."""
    anahtar = acilis_anahtari(marka_kod)
    pub = (getattr(settings, 'R2_PUBLIC_URL', '') or '').rstrip('/')
    if r2_acik_mi() and pub:
        return '%s/%s' % (pub, anahtar)
    return '%s%s' % (settings.MEDIA_URL if settings.MEDIA_URL.startswith('/') else '/' + settings.MEDIA_URL, anahtar)


def acilis_veri(marka):
    """QR sitesinin okuyacağı sözlük. Yalnızca 'Yayında' görseller gider; tarih filtresini site uygular."""
    gorseller = []
    for g in marka.acilis_gorselleri.filter(aktif=True).order_by('sira', 'id'):
        u = g.url()
        if not u:
            continue
        gorseller.append({'url': u, 'baslik': g.baslik,
                          'baslangic': g.baslangic.isoformat() if g.baslangic else '',
                          'bitis': g.bitis.isoformat() if g.bitis else ''})
    veri = {'aktif': bool(marka.acilis_aktif), 'sure_sn': int(marka.acilis_sure_sn),
            'atlanabilir': bool(marka.acilis_atlanabilir), 'gunde_bir': bool(marka.acilis_gunde_bir),
            'gorseller': gorseller}
    # 'surum': içerik değişince değişir; "günde bir kez" ayarı yeni kampanyada yeniden gösterir.
    veri['surum'] = hashlib.md5(json.dumps(veri, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:12]
    veri['guncelleme'] = timezone.now().isoformat(timespec='seconds')
    return veri


def acilis_yayinla(marka):
    """(basarili, hata_metni). Hata durumunda istisna fırlatmaz; kayıt geri alınmaz."""
    try:
        icerik = json.dumps(acilis_veri(marka), ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        dosyaya_yaz(acilis_anahtari(marka.kod), icerik, 'application/json; charset=utf-8')
    except Exception as e:
        hata = ('%s: %s' % (e.__class__.__name__, e))[:380]
        marka.acilis_yayin_hata = hata
        marka.save(update_fields=['acilis_yayin_hata'])
        return False, hata
    marka.acilis_son_yayin = timezone.now()
    marka.acilis_yayin_hata = ''
    marka.save(update_fields=['acilis_son_yayin', 'acilis_yayin_hata'])
    return True, ''


def _gorsel_hazirla(dosya, marka_kod):
    """En uzun kenarı 1600px'e küçültür; şeffaf PNG'yi korur, diğerlerini JPEG yapar."""
    from PIL import Image, ImageOps
    dosya.seek(0)
    img = Image.open(dosya)
    img = ImageOps.exif_transpose(img)
    alfa = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
    if max(img.size) > MAX_KENAR:
        img.thumbnail((MAX_KENAR, MAX_KENAR), Image.LANCZOS)
    cikis = BytesIO()
    if alfa:
        img.convert('RGBA').save(cikis, 'PNG', optimize=True)
        uzanti = 'png'
    else:
        img.convert('RGB').save(cikis, 'JPEG', quality=86, optimize=True)
        uzanti = 'jpg'
    return '%s-acilis-%s.%s' % (marka_kod, uuid.uuid4().hex[:10], uzanti), ContentFile(cikis.getvalue())


def _tarih(ham):
    ham = (ham or '').strip()
    if not ham:
        return None
    return datetime.date.fromisoformat(ham)


def _sil_dosya(alan):
    try:
        if alan and alan.name:
            alan.storage.delete(alan.name)
    except Exception:
        pass


def _yayinla_ve_bildir(request, marka, metin):
    ok, hata = acilis_yayinla(marka)
    if ok:
        messages.success(request, metin + ' QR sitesinde en geç 1 dakikada görünür.')
    else:
        messages.error(request, 'Kayıt yapıldı ancak QR sitesine YAYINLANAMADI: %s — "Yeniden yayınla" ile tekrar deneyin.' % hata)


def _sirayi_normalle(marka):
    for i, g in enumerate(marka.acilis_gorselleri.order_by('sira', 'id'), 1):
        if g.sira != i * 10:
            g.sira = i * 10
            g.save(update_fields=['sira'])


def menu_acilis(request, marka_kod):
    from .menu_views import _giris, _marka_al, _ctx
    personel, yanit = _giris(request)
    if yanit:
        return yanit
    marka = _marka_al(marka_kod)

    if request.method == 'POST':
        islem = request.POST.get('islem', '')
        if islem == 'ayar':
            try:
                sure = int(request.POST.get('sure_sn', ''))
            except ValueError:
                sure = 0
            if not (SURE_MIN <= sure <= SURE_MAX):
                messages.error(request, 'Süre %d ile %d saniye arasında olmalı.' % (SURE_MIN, SURE_MAX))
            else:
                marka.acilis_aktif = request.POST.get('aktif') == 'on'
                marka.acilis_sure_sn = sure
                marka.acilis_atlanabilir = request.POST.get('atlanabilir') == 'on'
                marka.acilis_gunde_bir = request.POST.get('gunde_bir') == 'on'
                marka.save(update_fields=['acilis_aktif', 'acilis_sure_sn', 'acilis_atlanabilir', 'acilis_gunde_bir'])
                _yayinla_ve_bildir(request, marka, 'Ayarlar kaydedildi.' + ('' if marka.acilis_aktif else ' Açılış görseli KAPALI.'))
        elif islem == 'yukle':
            dosyalar = request.FILES.getlist('dosyalar')
            if request.POST.get('dosya_secildi') == '1' and not dosyalar:
                messages.error(request, 'Seçtiğin görsel sunucuya ulaşmadı. Dosya çok büyükse ya da bağlantı kesildiyse bu olur; yeniden dene.')
            elif not dosyalar:
                messages.error(request, 'Önce bir görsel seç.')
            else:
                mevcut = marka.acilis_gorselleri.count()
                eklenen, hatalar = 0, []
                for d in dosyalar:
                    if mevcut + eklenen >= MAX_GORSEL:
                        hatalar.append('En fazla %d görsel eklenebilir.' % MAX_GORSEL)
                        break
                    if d.size > MAX_DOSYA_MB * 1024 * 1024:
                        hatalar.append('%s: dosya %d MB üstünde.' % (d.name, MAX_DOSYA_MB))
                        continue
                    try:
                        ad, icerik = _gorsel_hazirla(d, marka.kod)
                    except Exception:
                        hatalar.append('%s: geçerli bir görsel değil (JPG, PNG veya WebP yükle).' % d.name)
                        continue
                    son = marka.acilis_gorselleri.aggregate(m=Max('sira'))['m'] or 0
                    g = MenuAcilisGorsel(marka=marka, baslik=(d.name.rsplit('.', 1)[0])[:80], sira=son + 10)
                    try:
                        g.gorsel.save(ad, icerik, save=False)
                        g.save()
                    except Exception as e:
                        hatalar.append('%s: yüklenemedi (%s).' % (d.name, e))
                        continue
                    eklenen += 1
                for h in hatalar:
                    messages.error(request, h)
                if eklenen:
                    _yayinla_ve_bildir(request, marka, '%d görsel eklendi.' % eklenen)
        elif islem in ('gorsel', 'sil', 'yukari', 'asagi'):
            try:
                g = marka.acilis_gorselleri.get(id=int(request.POST.get('id', '0')))
            except (ValueError, MenuAcilisGorsel.DoesNotExist):
                messages.error(request, 'Görsel bulunamadı.')
                return redirect('menu_acilis', marka_kod=marka.kod)
            if islem == 'sil':
                _sil_dosya(g.gorsel)
                g.delete()
                _sirayi_normalle(marka)
                _yayinla_ve_bildir(request, marka, 'Görsel silindi.')
            elif islem in ('yukari', 'asagi'):
                _sirayi_normalle(marka)
                liste = list(marka.acilis_gorselleri.order_by('sira', 'id'))
                i = next((k for k, x in enumerate(liste) if x.id == g.id), None)
                j = None if i is None else (i - 1 if islem == 'yukari' else i + 1)
                if j is not None and 0 <= j < len(liste):
                    a, b = liste[i], liste[j]
                    a.sira, b.sira = b.sira, a.sira
                    a.save(update_fields=['sira'])
                    b.save(update_fields=['sira'])
                    _yayinla_ve_bildir(request, marka, 'Sıra değişti.')
            else:
                try:
                    bas, bit = _tarih(request.POST.get('baslangic')), _tarih(request.POST.get('bitis'))
                except ValueError:
                    messages.error(request, 'Tarih geçersiz.')
                    return redirect('menu_acilis', marka_kod=marka.kod)
                if bas and bit and bit < bas:
                    messages.error(request, 'Bitiş tarihi başlangıçtan önce olamaz.')
                else:
                    g.baslik = (request.POST.get('baslik') or '').strip()[:80]
                    g.aktif = request.POST.get('aktif') == 'on'
                    g.baslangic, g.bitis = bas, bit
                    g.save(update_fields=['baslik', 'aktif', 'baslangic', 'bitis'])
                    _yayinla_ve_bildir(request, marka, 'Görsel kaydedildi.')
        elif islem == 'yayinla':
            ok, hata = acilis_yayinla(marka)
            (messages.success if ok else messages.error)(request, 'Açılış görseli QR sitesine yayınlandı.' if ok else 'Yayınlanamadı: %s' % hata)
        return redirect('menu_acilis', marka_kod=marka.kod)

    bugun = timezone.localdate()
    gorseller = list(marka.acilis_gorselleri.order_by('sira', 'id'))
    for g in gorseller:
        if not g.aktif:
            g.durum = ('pasif', 'Kapalı')
        elif g.baslangic and g.baslangic > bugun:
            g.durum = ('bekliyor', '%s tarihinde başlar' % g.baslangic.strftime('%d.%m.%Y'))
        elif g.bitis and g.bitis < bugun:
            g.durum = ('bitti', 'Süresi doldu')
        else:
            g.durum = ('canli', 'Şu an gösteriliyor')
    canli = [g for g in gorseller if g.durum[0] == 'canli']
    ctx = _ctx(request, personel, marka, gorseller=gorseller, canli=canli,
               toplam_sn=len(canli) * marka.acilis_sure_sn, json_adres=acilis_adresi(marka.kod),
               max_gorsel=MAX_GORSEL, sure_min=SURE_MIN, sure_max=SURE_MAX,
               canli_urller=[g.url() for g in canli])
    return render(request, 'menu_acilis.html', ctx)
