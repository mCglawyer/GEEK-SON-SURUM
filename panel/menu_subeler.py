"""QR Menü — şube bazlı ürün müsaitliği.

Tüm şubelere aynı QR gider; müşteri QR'ı açınca şubesini seçer (ya da adresteki ?sube=kod ile otomatik seçilir)
ve yalnızca o şubede satılan ürünleri görür. Hangi ürün hangi şubede YOK bilgisi, CSV şemasına dokunmamak için
ayrı bir statik JSON'da yayınlanır: menu/<marka>-subeler.json. Varsayılan "her şubede var"dır; yeni eklenen ürün
ve yeni eklenen şube kendiliğinden her yerde görünür.
"""
import hashlib
import json

from django.conf import settings
from django.contrib import messages
from django.db.models import Max
from django.shortcuts import redirect, render
from django.utils import timezone

from . import menu_yayin
from .models import MenuSube, MenuUrun, Sube


def subeler_anahtari(marka_kod):
    return 'menu/%s-subeler.json' % marka_kod


def subeler_adresi(marka_kod):
    anahtar = subeler_anahtari(marka_kod)
    pub = (getattr(settings, 'R2_PUBLIC_URL', '') or '').rstrip('/')
    if menu_yayin.r2_acik_mi() and pub:
        return '%s/%s' % (pub, anahtar)
    return '%s%s' % (settings.MEDIA_URL if settings.MEDIA_URL.startswith('/') else '/' + settings.MEDIA_URL, anahtar)


def subeler_veri(marka):
    """Sitenin okuyacağı sözlük. Yalnızca seçilebilir (aktif) şubeler gider."""
    subeler = list(marka.menu_subeleri.filter(aktif=True))
    kodlar = {s.id: s.kod for s in subeler}
    yok = {}
    through = MenuUrun.gizli_subeler.through
    for urun_kod, sube_id in (through.objects.filter(menuurun__marka=marka, menusube_id__in=kodlar)
                              .values_list('menuurun__kod', 'menusube_id').order_by('menuurun__kod')):
        yok.setdefault(urun_kod, []).append(kodlar[sube_id])
    veri = {'subeler': [{'kod': s.kod, 'ad': s.ad} for s in subeler], 'yok': yok}
    veri['surum'] = hashlib.md5(json.dumps(veri, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:12]
    veri['guncelleme'] = timezone.now().isoformat(timespec='seconds')
    return veri


def subeler_yayinla(marka):
    """(basarili, hata_metni). İstisna fırlatmaz."""
    try:
        icerik = json.dumps(subeler_veri(marka), ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        menu_yayin.dosyaya_yaz(subeler_anahtari(marka.kod), icerik, 'application/json; charset=utf-8')
    except Exception as e:
        return False, ('%s: %s' % (e.__class__.__name__, e))[:380]
    return True, ''


def _yayinla_ve_bildir(request, marka, metin):
    ok, hata = subeler_yayinla(marka)
    if ok:
        messages.success(request, metin + ' QR menüsü güncellendi (en geç 1 dakikada sitede görünür).')
    else:
        messages.error(request, 'Kayıt yapıldı ancak QR sitesine YAYINLANAMADI: %s' % hata)


def _kod_uret(marka, ad):
    from .menu_views import tr_slug
    taban = tr_slug(ad)[:36] or 'sube'
    kod, n = taban, 2
    while marka.menu_subeleri.filter(kod=kod).exists():
        kod = '%s-%d' % (taban, n)
        n += 1
    return kod


def _sirayi_normalle(marka):
    for i, s in enumerate(marka.menu_subeleri.order_by('sira', 'ad', 'id'), 1):
        if s.sira != i * 10:
            s.sira = i * 10
            s.save(update_fields=['sira'])


def menu_subeler(request, marka_kod):
    from .menu_views import _giris, _marka_al, _ctx
    personel, yanit = _giris(request)
    if yanit:
        return yanit
    marka = _marka_al(marka_kod)

    if request.method == 'POST':
        islem = request.POST.get('islem', '')
        if islem == 'ekle':
            adlar = []
            for sid in request.POST.getlist('panel_sube'):
                try:
                    adlar.append(Sube.objects.get(id=int(sid)).ad)
                except (ValueError, Sube.DoesNotExist):
                    pass
            yeni = (request.POST.get('ad') or '').strip()
            if yeni:
                adlar.append(yeni)
            mevcut_adlar = {s.ad.casefold() for s in marka.menu_subeleri.all()}
            eklenen = 0
            for ad in adlar:
                ad = ad.strip()[:80]
                if not ad or ad.casefold() in mevcut_adlar:
                    continue
                son = marka.menu_subeleri.aggregate(m=Max('sira'))['m'] or 0
                MenuSube.objects.create(marka=marka, ad=ad, kod=_kod_uret(marka, ad), sira=son + 10)
                mevcut_adlar.add(ad.casefold())
                eklenen += 1
            if eklenen:
                _yayinla_ve_bildir(request, marka, '%d şube eklendi.' % eklenen)
            else:
                messages.error(request, 'Eklenecek yeni bir şube seçilmedi ya da bu ad zaten listede.')
        elif islem in ('duzenle', 'sil', 'yukari', 'asagi'):
            try:
                s = marka.menu_subeleri.get(id=int(request.POST.get('id', '0')))
            except (ValueError, MenuSube.DoesNotExist):
                messages.error(request, 'Şube bulunamadı.')
                return redirect('menu_subeler', marka_kod=marka.kod)
            if islem == 'sil':
                s.delete()
                _sirayi_normalle(marka)
                _yayinla_ve_bildir(request, marka, 'Şube silindi.')
            elif islem == 'duzenle':
                ad = (request.POST.get('ad') or '').strip()[:80]
                if not ad:
                    messages.error(request, 'Şube adı boş olamaz.')
                else:
                    s.ad = ad
                    s.aktif = request.POST.get('aktif') == 'on'
                    s.save(update_fields=['ad', 'aktif'])
                    _yayinla_ve_bildir(request, marka, 'Şube kaydedildi.')
            else:
                _sirayi_normalle(marka)
                liste = list(marka.menu_subeleri.order_by('sira', 'id'))
                i = next((k for k, x in enumerate(liste) if x.id == s.id), None)
                j = None if i is None else (i - 1 if islem == 'yukari' else i + 1)
                if j is not None and 0 <= j < len(liste):
                    a, b = liste[i], liste[j]
                    a.sira, b.sira = b.sira, a.sira
                    a.save(update_fields=['sira'])
                    b.save(update_fields=['sira'])
                    _yayinla_ve_bildir(request, marka, 'Sıra değişti.')
        elif islem == 'matris':
            subeler = list(marka.menu_subeleri.all())
            urunler = {u.id: u for u in marka.urunler.all()}
            gorulen = set()
            for h in request.POST.getlist('urun_ids'):
                try:
                    if int(h) in urunler:
                        gorulen.add(int(h))
                except ValueError:
                    pass
            for s in subeler:
                gizli = [uid for uid in gorulen if request.POST.get('v_%d_%d' % (uid, s.id)) != 'on']
                korunan = [u.id for u in s.gizli_urunler.all() if u.id not in gorulen]
                s.gizli_urunler.set(gizli + korunan)
            _yayinla_ve_bildir(request, marka, 'Şube – ürün seçimleri kaydedildi.')
        elif islem == 'yayinla':
            ok, hata = subeler_yayinla(marka)
            (messages.success if ok else messages.error)(
                request, 'Şube listesi QR sitesine yayınlandı.' if ok else 'Yayınlanamadı: %s' % hata)
        return redirect('menu_subeler', marka_kod=marka.kod)

    subeler = list(marka.menu_subeleri.all())
    urunler = list(marka.urunler.select_related('kategori').order_by('kategori__sira', 'kategori__id', 'sira', 'id'))
    gizli = {}
    for uid, sid in MenuUrun.gizli_subeler.through.objects.filter(menuurun__marka=marka).values_list('menuurun_id', 'menusube_id'):
        gizli.setdefault(uid, set()).add(sid)
    gruplar, son_kat = [], None
    for u in urunler:
        if u.kategori_id != son_kat:
            gruplar.append({'kategori': u.kategori, 'satirlar': []})
            son_kat = u.kategori_id
        h = gizli.get(u.id, set())
        gruplar[-1]['satirlar'].append({'urun': u, 'hucreler': [(s, s.id not in h) for s in subeler],
                                        'yok_sayisi': len(h)})
    eklenebilir = []
    mevcut = {s.ad.casefold() for s in subeler}
    for ps in Sube.objects.filter(depo_mu=False).order_by('ad'):
        if ps.ad.casefold() not in mevcut:
            eklenebilir.append(ps)
    ctx = _ctx(request, personel, marka, subeler=subeler, gruplar=gruplar, eklenebilir=eklenebilir,
               json_adres=subeler_adresi(marka.kod), site_adresi_ornek='?sube=%s' % (subeler[0].kod if subeler else 'sube-kodu'),
               toplam_yok=sum(len(v) for v in gizli.values()))
    return render(request, 'menu_subeler.html', ctx)
