"""Mutfak zayi — yazılı kayıt, günlük liste ve rapor (Excel / PDF).

Ekranlar:
  /mutfak/zayi/        Mutfak personeli + mutfak sorumlusu zayiyi yazar; yetkili roller gün gün görür.
  /mutfak/zayi/rapor/  Gün / hafta / ay / tarih aralığı raporu, şubeler arası karşılaştırma,
                       Excel ve PDF indirme.
"""
import datetime
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import (MutfakMaliyetKalemi, MutfakZayi, MutfakZayiKalemi, Rol, ZayiBirim,
                     zayi_urun_anahtar, zayi_urun_baslik)
from .views import _aktif_personel, _cikis_mi, _logout
from . import zayi_rapor
from .zayi_kapsam import (ZAYI_GIRIS_ROLLERI, ZAYI_RAPOR_ROLLERI, mutfakli_subeler,
                          personel_giris_subesi, zayi_subeleri)

SATIR_SAYISI = 5            # formda açılan boş satır
SATIR_MAKS = 40             # tek seferde en fazla satır
MIKTAR_MAKS = Decimal('1000000')
GERIYE_DONUK_GUN = 60       # sorumlu, geçmiş güne kayıt girebilir (personel yalnız bugüne)
SATIR_LISTE_MAKS = 500      # sayfadaki rapor dökümü (Excel / PDF'te sınır yok)
ESKI_FOTO_SAKLAMA_GUN = 35  # eski fotoğraflı kayıtlar (yeni sistemde fotoğraf yok)

BIRIMLER = [b for b, _ in ZayiBirim.choices]


# ---- yardımcılar ------------------------------------------------------------------
def _giris(request, roller):
    """(personel, yönlendirme). Oturum yoksa / rol uygun değilse yönlendirme dolu gelir."""
    if not request.user.is_authenticated:
        return None, redirect('ana_sayfa')
    if _cikis_mi(request):
        return None, _logout(request)
    personel = _aktif_personel(request)
    if personel is None or personel.rol not in roller:
        return None, redirect('ana_sayfa')
    return personel, None


_BIN = re.compile(r'^[1-9]\d{0,2}(\.\d{3})+$')


def miktar_oku(metin):
    """'100' '1,5' '1.5' '1.250' -> Decimal. '1.250' = bin iki yüz elli (Türkçe yazım);
    '0.125' ondalıktır. Geçersiz / sıfır / çok büyük ise None."""
    s = (metin or '').strip().replace(' ', '')
    if not s:
        return None
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif _BIN.match(s):
        s = s.replace('.', '')
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    if not d.is_finite() or d <= 0 or d > MIKTAR_MAKS:
        return None
    return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _tarih_oku(metin, varsayilan):
    return zayi_rapor.tarih_oku(metin, varsayilan)


def _urun_onerileri():
    """Yazım hatasını azaltmak için öneri listesi: tanımlı maliyet kalemleri + daha önce
    girilmiş ürünler (en çok kullanılandan başlayarak)."""
    from django.db.models import Count
    isimler = {}
    for ad in MutfakMaliyetKalemi.objects.values_list('ad', flat=True):
        isimler[zayi_urun_baslik(zayi_urun_anahtar(ad))] = 1
    son = timezone.localdate() - datetime.timedelta(days=120)
    for r in (MutfakZayiKalemi.objects.filter(tarih__gte=son, sube__mutfak_var=True)
              .values('urun_anahtar').annotate(n=Count('id')).order_by('-n')[:300]):
        isimler.setdefault(zayi_urun_baslik(r['urun_anahtar']), 1)
    return list(isimler)[:400]


def _eski_foto_temizle():
    sinir = timezone.now() - datetime.timedelta(days=ESKI_FOTO_SAKLAMA_GUN)
    for z in MutfakZayi.objects.filter(olusturma__lt=sinir):
        try:
            if z.foto:
                z.foto.delete(save=False)
        except Exception:
            pass
        z.delete()


def _satirlari_oku(post):
    """Formdaki satırlar -> [(urun, miktar_metin, birim, aciklama)], tamamen boş satırlar atılır."""
    urunler = post.getlist('urun')
    miktarlar = post.getlist('miktar')
    birimler = post.getlist('birim')
    aciklamalar = post.getlist('aciklama')
    cikti = []
    for i in range(min(len(urunler), SATIR_MAKS * 2)):
        urun = (urunler[i] or '').strip()
        miktar = (miktarlar[i] if i < len(miktarlar) else '').strip()
        birim = (birimler[i] if i < len(birimler) else '').strip()
        aciklama = (aciklamalar[i] if i < len(aciklamalar) else '').strip()
        if not (urun or miktar or aciklama):
            continue
        cikti.append((urun, miktar, birim, aciklama))
    return cikti


# ---- Ana sayfa: yaz + gün listesi -------------------------------------------------
def mutfak_zayi_sayfa(request):
    izinli = tuple(set(ZAYI_GIRIS_ROLLERI) | set(ZAYI_RAPOR_ROLLERI))
    personel, red = _giris(request, izinli)
    if red:
        return red
    _eski_foto_temizle()

    bugun = timezone.localdate()
    ekleyebilir = personel.rol in ZAYI_GIRIS_ROLLERI
    rapor_gorebilir = personel.rol in ZAYI_RAPOR_ROLLERI
    sorumlu = personel.rol == Rol.MUTFAK_SORUMLUSU

    # Görebileceği (kapsamdaki) mutfaklı şubeler
    subeler = zayi_subeleri(personel)
    sube_idleri = [s.id for s in subeler]

    # Personelin yazacağı şube (bugünkü atama / kendi şubesi) ve engel nedeni
    giris_subesi = None
    engel = ''
    if ekleyebilir:
        if personel.rol == Rol.MUTFAK_PERSONEL:
            giris_subesi = personel_giris_subesi(personel)
            if giris_subesi is None:
                engel = ("Bugün için mutfağı olan bir şubeye atamanız görünmüyor. Yöneticinizden "
                         "şube atamasını (ya da şubede 'Mutfağı var' ayarını) kontrol etmesini isteyin.")
        elif not subeler:
            engel = "Sistemde 'Mutfağı var' olarak işaretli şube yok. Şubeler sayfasından Genel Müdür işaretleyebilir."

    if request.method == 'POST':
        islem = request.POST.get('islem')
        if islem == 'zayi_ekle' and ekleyebilir and not engel:
            return _zayi_ekle(request, personel, bugun, subeler, giris_subesi, sorumlu)
        if islem == 'zayi_sil':
            _zayi_sil(request, personel, sube_idleri, bugun)
            return redirect(request.get_full_path())
        return redirect('mutfak_zayi')

    return _sayfayi_ciz(request, personel, bugun, subeler, sube_idleri, giris_subesi, engel,
                        ekleyebilir, rapor_gorebilir, sorumlu)


def _sayfayi_ciz(request, personel, bugun, subeler, sube_idleri, giris_subesi, engel,
                 ekleyebilir, rapor_gorebilir, sorumlu, satirlar=None, form_tarih=None, form_sube=None):
    secili_tarih = min(_tarih_oku(request.GET.get('tarih') or request.GET.get('mz_tarih'), bugun), bugun)
    sec = request.GET.get('sube')
    secili_sube = int(sec) if sec and sec.isdigit() and int(sec) in sube_idleri else 0
    filtre = [secili_sube] if secili_sube else sube_idleri

    liste = (MutfakZayiKalemi.objects.filter(sube_id__in=filtre, tarih=secili_tarih)
             .select_related('sube', 'personel').order_by('sube__ad', 'olusturma'))
    kayitlar = []
    for k in liste:
        kayitlar.append({
            'k': k,
            'sube': zayi_rapor.sube_adi(k), 'giren': zayi_rapor.giren_adi(k),
            'miktar': zayi_rapor.kalem_miktar_yaz(k),
            'silinebilir': _silebilir(personel, k, sube_idleri, bugun),
        })

    eski = []
    if rapor_gorebilir or personel.rol == Rol.MUTFAK_PERSONEL:
        gun_bas = datetime.datetime.combine(secili_tarih, datetime.time.min, tzinfo=timezone.get_current_timezone())
        eski = list(MutfakZayi.objects.filter(
            sube_id__in=filtre, olusturma__gte=gun_bas, olusturma__lt=gun_bas + datetime.timedelta(days=1)
        ).select_related('sube', 'personel').order_by('-olusturma'))

    bos = SATIR_SAYISI
    if satirlar is None:
        satirlar = [{'urun': '', 'miktar': '', 'birim': 'gr', 'aciklama': ''} for _ in range(bos)]

    return render(request, 'mutfak_zayi.html', {
        'personel': personel, 'aktif': 'mutfak_zayi',
        'ekleyebilir': ekleyebilir and not engel, 'engel': engel,
        'rapor_gorebilir': rapor_gorebilir, 'sorumlu': sorumlu,
        'subeler': subeler, 'secili_sube': secili_sube,
        'giris_subesi': giris_subesi,
        'secili_tarih': secili_tarih.strftime('%Y-%m-%d'), 'bugun': bugun.strftime('%Y-%m-%d'),
        'en_eski_giris': (bugun - datetime.timedelta(days=GERIYE_DONUK_GUN)).strftime('%Y-%m-%d'),
        'kayitlar': kayitlar, 'eski_kayitlar': eski,
        'satirlar': satirlar, 'birimler': BIRIMLER,
        'oneriler': _urun_onerileri() if ekleyebilir else [],
        'form_tarih': form_tarih or bugun.strftime('%Y-%m-%d'),
        'form_sube': form_sube or (subeler[0].id if len(subeler) == 1 else 0),
        'satir_maks': SATIR_MAKS,
    })


def _silebilir(personel, k, sube_idleri, bugun):
    if personel.rol == Rol.MUTFAK_SORUMLUSU:
        return k.sube_id in sube_idleri
    if personel.rol == Rol.MUTFAK_PERSONEL:
        return k.personel_id == personel.id and k.tarih == bugun
    return False


def _zayi_sil(request, personel, sube_idleri, bugun):
    pk = request.POST.get('kalem_id', '')
    if not pk.isdigit():
        return
    k = MutfakZayiKalemi.objects.filter(id=int(pk)).select_related('sube').first()
    if k is None:
        return
    if _silebilir(personel, k, sube_idleri, bugun):
        k.delete()
        messages.success(request, "Zayi satırı silindi: %s" % k.urun)
    else:
        messages.error(request, "Bu kaydı silme yetkiniz yok. Personel yalnızca kendi bugünkü kaydını silebilir.")


def _zayi_ekle(request, personel, bugun, subeler, giris_subesi, sorumlu):
    satirlar = _satirlari_oku(request.POST)
    # Tarih / şube kuralları
    if sorumlu:
        tarih = _tarih_oku(request.POST.get('tarih'), bugun)
        sube_id = request.POST.get('sube_id', '')
        sube = next((s for s in subeler if str(s.id) == sube_id), None)
    else:
        tarih = bugun
        sube = giris_subesi

    hatalar = []
    if sube is None:
        hatalar.append("Şube seçmelisiniz.")
    if tarih > bugun or tarih < bugun - datetime.timedelta(days=GERIYE_DONUK_GUN):
        hatalar.append("Tarih bugünden ileri ya da %d günden eski olamaz." % GERIYE_DONUK_GUN)
    if not satirlar:
        hatalar.append("En az bir ürün yazmalısınız.")
    if len(satirlar) > SATIR_MAKS:
        hatalar.append("Tek seferde en fazla %d satır girilebilir." % SATIR_MAKS)

    temiz = []
    form_satirlari = []
    for i, (urun, miktar_metin, birim, aciklama) in enumerate(satirlar[:SATIR_MAKS], 1):
        form_satirlari.append({'urun': urun, 'miktar': miktar_metin,
                               'birim': birim if birim in BIRIMLER else 'gr', 'aciklama': aciklama})
        if not urun:
            hatalar.append("%d. satır: ürün adı boş." % i)
            continue
        if len(urun) > 120:
            hatalar.append("%d. satır: ürün adı en fazla 120 karakter olabilir." % i)
            continue
        miktar = miktar_oku(miktar_metin)
        if miktar is None:
            hatalar.append("%d. satır (%s): miktar geçersiz. Örn. 100 veya 1,5 yazın." % (i, urun))
            continue
        if birim not in BIRIMLER:
            hatalar.append("%d. satır (%s): birim seçin." % (i, urun))
            continue
        temiz.append((urun, miktar, birim, aciklama[:500]))

    if hatalar:
        for h in hatalar[:8]:
            messages.error(request, h)
        # Girilenleri kaybetmeden formu tekrar göster
        while len(form_satirlari) < SATIR_SAYISI:
            form_satirlari.append({'urun': '', 'miktar': '', 'birim': 'gr', 'aciklama': ''})
        return _sayfayi_ciz(request, personel, bugun, subeler, [s.id for s in subeler], giris_subesi, '',
                            True, personel.rol in ZAYI_RAPOR_ROLLERI, sorumlu, satirlar=form_satirlari,
                            form_tarih=tarih.strftime('%Y-%m-%d'), form_sube=sube.id if sube else 0)

    with transaction.atomic():
        for urun, miktar, birim, aciklama in temiz:
            MutfakZayiKalemi(sube=sube, personel=personel, personel_ad_arsiv=personel.ad_soyad,
                             tarih=tarih, urun=urun, miktar=miktar, birim=birim,
                             aciklama=aciklama).save()
    messages.success(request, "%d zayi satırı kaydedildi (%s · %s)." % (
        len(temiz), sube.ad, tarih.strftime('%d.%m.%Y')))
    return redirect('/mutfak/zayi/?tarih=%s%s' % (tarih.strftime('%Y-%m-%d'),
                                                   '&sube=%d' % sube.id if sorumlu else ''))


# ---- Rapor ------------------------------------------------------------------------
def mutfak_zayi_rapor(request):
    personel, red = _giris(request, ZAYI_RAPOR_ROLLERI)
    if red:
        return red
    bugun = timezone.localdate()
    subeler_hepsi = zayi_subeleri(personel)
    if not subeler_hepsi:
        messages.error(request, "Kapsamınızda mutfağı olan şube bulunmuyor.")
        return redirect('ana_sayfa')

    sec = request.GET.get('sube', '')
    secili = next((s for s in subeler_hepsi if str(s.id) == sec), None)
    subeler = [secili] if secili else subeler_hepsi

    donem, bas, bit, etiket, onceki, sonraki, uyari = zayi_rapor.donem_hesapla(
        request.GET.get('donem', 'gun'),
        _tarih_oku(request.GET.get('tarih'), bugun),
        _tarih_oku(request.GET.get('bas'), None), _tarih_oku(request.GET.get('bit'), None))
    veri = zayi_rapor.rapor_verisi(subeler, bas, bit)
    sube_etiketi = secili.ad if secili else ('Tüm şubeler' if len(subeler_hepsi) > 1 else subeler_hepsi[0].ad)

    bicim = request.GET.get('bicim', '')
    dosya_adi = 'mutfak-zayi_%s_%s' % (bas.strftime('%Y%m%d'), bit.strftime('%Y%m%d'))
    if bicim == 'xlsx':
        yanit = HttpResponse(zayi_rapor.excel_bytes(veri, etiket, sube_etiketi),
                             content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        yanit['Content-Disposition'] = 'attachment; filename="%s.xlsx"' % dosya_adi
        return yanit
    if bicim == 'pdf':
        yanit = HttpResponse(zayi_rapor.pdf_bytes(veri, etiket, sube_etiketi), content_type='application/pdf')
        yanit['Content-Disposition'] = 'attachment; filename="%s.pdf"' % dosya_adi
        return yanit

    def _url(**ek):
        q = {'donem': donem, 'tarih': (ek.pop('tarih', None) or bas).strftime('%Y-%m-%d')}
        if secili:
            q['sube'] = secili.id
        if donem == 'ozel':
            q['bas'], q['bit'] = bas.strftime('%Y-%m-%d'), bit.strftime('%Y-%m-%d')
        q.update(ek)
        return '?' + '&'.join('%s=%s' % (k, v) for k, v in q.items())

    detay = veri['detay']
    detay_gorunen = [{
        'tarih': k.tarih, 'sube': zayi_rapor.sube_adi(k), 'urun': k.urun,
        'miktar': zayi_rapor.kalem_miktar_yaz(k), 'giren': zayi_rapor.giren_adi(k), 'aciklama': k.aciklama,
    } for k in detay[:SATIR_LISTE_MAKS]]

    return render(request, 'mutfak_zayi_rapor.html', {
        'personel': personel, 'aktif': 'mutfak_zayi', 'veri': veri, 'donemler': zayi_rapor.DONEMLER,
        'donem': donem, 'bas': bas.strftime('%Y-%m-%d'), 'bit': bit.strftime('%Y-%m-%d'),
        'tarih': (bas if donem != 'ozel' else bas).strftime('%Y-%m-%d'), 'etiket': etiket, 'uyari': uyari,
        'subeler_hepsi': subeler_hepsi, 'secili_sube': secili.id if secili else 0,
        'sube_etiketi': sube_etiketi, 'bugun': bugun.strftime('%Y-%m-%d'),
        'onceki_url': _url(tarih=onceki) if onceki else '', 'sonraki_url': _url(tarih=sonraki) if sonraki else '',
        'xlsx_url': _url(bicim='xlsx'), 'pdf_url': _url(bicim='pdf'),
        'detay': detay_gorunen, 'detay_toplam': len(detay), 'detay_kisaltildi': len(detay) > SATIR_LISTE_MAKS,
        'detay_maks': SATIR_LISTE_MAKS,
        'cok_sube': len(veri['subeler']) > 1,
    })
