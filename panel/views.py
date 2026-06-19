import json
import datetime
import random
import secrets
import unicodedata
import base64
from decimal import Decimal, InvalidOperation
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum
from django.core.files.base import ContentFile
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User

from .models import (Personel, KodKilit, Vardiya, Mola, Sube, Puantaj, Zayi, Birim, Kalibrasyon, Irsaliye,
                     StokUrun, StokSayim, StokSayimKalem,
                     SevkiyatTalep, SevkiyatKalem, SevkiyatBirim, SevkiyatDurumu,
                     SevkiyatForm, Urun, SiparisHareket,
                     KahveSoru, GunlukSoru, SoruAyar,
                     Rol, OnayDurumu, VardiyaTipi)
from .constants import GUNLUK_TOPLAM_MOLA_DK, BIRINCI_MOLA_DK, MOLA_LIMIT_UYARI_DK
from .hukuki_icerik import HUKUKI_SAYFALAR

MAX_DENEME = 5
KILIT_DK = 10
MODEL_BACKEND = 'django.contrib.auth.backends.ModelBackend'
GUN_ADLARI = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
UST_YONETIM = [Rol.GENEL_MUDUR, Rol.MUDUR, Rol.OPERATOR, Rol.YATIRIMCI]
# Tam yetkili roller (Ekip yönetimi, şube atama, çıkış onayı gibi GM düzeyi yetkiler)
TAM_YETKILI = [Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI]
# Şifreyle giren, şubeye bağlı olmayan ofis/birim rolleri (Ekip'ten açılır)
OFIS_ROLLERI = [Rol.GENEL_MUDUR, Rol.MUDUR, Rol.OPERATOR, Rol.YATIRIMCI, Rol.SATIN_ALMA, Rol.SEVKIYAT]
CALISMA_TIPLERI = [VardiyaTipi.SABAHCI, VardiyaTipi.ARACI, VardiyaTipi.AKSAMCI]


# =========================================================================
# YARDIMCILAR
# =========================================================================
def _istemci_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or 'bilinmiyor'


def _hafta_gunleri(secili):
    today = timezone.localdate()
    bu = today - datetime.timedelta(days=today.weekday())
    start = bu if secili == 'bu' else bu + datetime.timedelta(days=7)
    return start, start + datetime.timedelta(days=6), [start + datetime.timedelta(days=i) for i in range(7)]


def _ay_araligi(ay_str):
    try:
        ilk = datetime.datetime.strptime((ay_str or '') + '-01', '%Y-%m-%d').date()
    except ValueError:
        ilk = timezone.localdate().replace(day=1)
    sonraki = ilk.replace(year=ilk.year + 1, month=1) if ilk.month == 12 else ilk.replace(month=ilk.month + 1)
    return ilk, sonraki


def _gun_araligi(request, bas_param, bit_param):
    """İki tarih (YYYY-MM-DD) GET parametresinden (bas, son_haric, bas_str, bit_str)
    döndürür. İkisi de geçerli değilse None. son_haric = bitiş + 1 gün (bitiş dahil)."""
    bas_str = (request.GET.get(bas_param) or '').strip()
    bit_str = (request.GET.get(bit_param) or '').strip()
    if not bas_str or not bit_str:
        return None
    try:
        bas = datetime.datetime.strptime(bas_str, '%Y-%m-%d').date()
        bit = datetime.datetime.strptime(bit_str, '%Y-%m-%d').date()
    except ValueError:
        return None
    if bit < bas:
        bas, bit = bit, bas
        bas_str, bit_str = bit_str, bas_str
    return bas, bit + datetime.timedelta(days=1), bas_str, bit_str


def _aktif_personel(request):
    return Personel.objects.filter(user=request.user).select_related('sube').first()


def _yonetici_sube(request, subeler):
    """Yöneticinin seçtiği şubeyi oturumda hatırlar (bölümler arası temiz URL)."""
    sid = request.GET.get('sube_id')
    if sid:
        request.session['sel_sube_id'] = sid
    else:
        sid = request.session.get('sel_sube_id')
    sel = next((s for s in subeler if str(s.id) == str(sid)), None)
    if sel is None:
        sel = next((s for s in subeler if not s.depo_mu), subeler[0] if subeler else None)
    return sel


def _yon_subeler(personel):
    """Yöneticinin görebileceği şubeler. Bölge Müdürü yalnızca atandığı şubeleri,
    Genel Müdür/Operatör tüm şubeleri görür."""
    if personel and personel.rol == Rol.MUDUR:
        return list(personel.sorumlu_subeler.order_by('ad'))
    return list(Sube.objects.order_by('ad'))


def _vardiya_tablo(personeller, start, end, gunler):
    shifts = list(Vardiya.objects.filter(personel__in=personeller, tarih__range=[start, end])) if personeller else []
    smap = {(v.personel_id, v.tarih): v for v in shifts}
    rows = [{'personel': p, 'hucreler': [{'tarih': g, 'vardiya': smap.get((p.id, g))} for g in gunler]}
            for p in personeller]
    d = set(v.durum for v in shifts)
    if OnayDurumu.ONAY_BEKLIYOR in d:
        durum, sinif = 'Onay Bekliyor', 'badge-wait'
    elif OnayDurumu.REDDEDILDI in d:
        durum, sinif = 'Reddedildi', 'badge-no'
    elif OnayDurumu.ONAYLANDI in d:
        durum, sinif = 'Onaylandı', 'badge-ok'
    elif OnayDurumu.TASLAK in d:
        durum, sinif = 'Taslak', 'badge-info'
    else:
        durum, sinif = 'Planlanmadı', 'badge-info'
    red = next((v.red_notu for v in shifts if v.durum == OnayDurumu.REDDEDILDI and v.red_notu), None)
    return {
        'rows': rows, 'hafta_durum': durum, 'durum_sinif': sinif,
        'red_notu': red, 'onay_bekleyen': OnayDurumu.ONAY_BEKLIYOR in d,
        'onaya_gonderilebilir': bool(d & {OnayDurumu.TASLAK, OnayDurumu.REDDEDILDI}),
        'gun_basliklari': [{'gun_adi': GUN_ADLARI[i], 'tarih': g} for i, g in enumerate(gunler)],
    }


def _puantaj_hesapla(personel, bas, son, manuel_ay=None):
    """[bas, son) aralığında puantaj sayıları. manuel_ay verilirse o aya ait
    manuel düzenlenmiş kayıt öncelikli kullanılır (aylık mod)."""
    if manuel_ay is not None:
        rec = Puantaj.objects.filter(personel=personel, ay=manuel_ay).first()
        if rec and rec.manuel_duzenlendi:
            return {'calisilan': rec.calisilan_gun, 'eksik': rec.eksik_gun,
                    'izinli': rec.izinli_gun, 'raporlu': rec.raporlu_gun, 'manuel': True}
    # Vardiya girildiği anda yansır (reddedilenler hariç)
    s = personel.vardiyalar.filter(tarih__gte=bas, tarih__lt=son).exclude(durum=OnayDurumu.REDDEDILDI)
    return {
        'calisilan': s.filter(vardiya_tipi__in=CALISMA_TIPLERI).count(),
        'izinli': s.filter(vardiya_tipi=VardiyaTipi.IZINLI).count(),
        'raporlu': s.filter(vardiya_tipi=VardiyaTipi.RAPORLU).count(),
        'eksik': s.filter(vardiya_tipi=VardiyaTipi.DEVAMSIZ).count(),
        'manuel': False,
    }


def _cikis_mi(request):
    return request.method == 'POST' and request.POST.get('islem') == 'cikis'


def _logout(request):
    auth_logout(request)
    request.session.flush()
    return redirect('ana_sayfa')


# =========================================================================
# ANA YÖNLENDİRME ( / )
# =========================================================================
def ana_sayfa(request):
    if not request.user.is_authenticated:
        if request.method == 'POST':
            islem = request.POST.get('islem')
            if islem == 'kod_giris':
                return _kod_giris(request)
            if islem == 'sifre_giris':
                return _sifre_giris(request)
            return redirect('ana_sayfa')
        return render(request, 'personel_giris.html')

    if _cikis_mi(request):
        return _logout(request)

    personel = _aktif_personel(request)
    if personel is None:
        return render(request, 'personel_panel.html', {'personel': None, 'yonetici_bekliyor': True, 'aktif': 'home'})
    if personel.rol in UST_YONETIM:
        return _yonetici_vardiya(request, personel)
    if personel.rol in (Rol.SATIN_ALMA, Rol.SEVKIYAT):
        return redirect('sevkiyat')
    if personel.rol == Rol.EGITMEN:
        return redirect('soru_yonetimi')
    if personel.rol in SORU_ROLLERI and _soru_sistemi_aktif():
        _gs = _gunluk_soru_getir_veya_ata(personel, timezone.localdate())
        if _gs is not None:
            _gunluk_finalize(_gs)
            if not _gs.cevaplandi:
                return redirect('gunluk_soru')
    if personel.rol == Rol.SEF:
        return _sef_home(request, personel)
    return _personel_home(request, personel)


# =========================================================================
# MOLA YARDIMCILARI (personel + şef ortak)
# =========================================================================
def _mola_toggle(request, personel):
    today = timezone.localdate()
    aktif = personel.molalar.filter(bitis_saati__isnull=True).order_by('-id').first()
    simdi = timezone.localtime().time()
    if aktif:
        aktif.bitis_saati = simdi
        aktif.save()
        messages.success(request, f"Molan bitti. Süre: {aktif.mola_suresi_dakika()} dk. İyi çalışmalar!")
    else:
        tamamlanan = personel.molalar.filter(tarih=today, bitis_saati__isnull=False).count()
        tip = '1. Mola' if tamamlanan == 0 else '2. Mola'
        personel.molalar.create(tarih=today, mola_tipi=tip, baslangic_saati=simdi)
        messages.success(request, "Molan başladı.")


def _mola_ctx(personel, today):
    aktif_mola = personel.molalar.filter(bitis_saati__isnull=True).order_by('-id').first()
    bugun_biten = personel.molalar.filter(tarih=today, bitis_saati__isnull=False)
    kullanilan = sum(m.mola_suresi_dakika() for m in bugun_biten)
    kalan_hak = max(0, GUNLUK_TOPLAM_MOLA_DK - kullanilan)
    start_iso, hedef_dk = '', GUNLUK_TOPLAM_MOLA_DK
    if aktif_mola and aktif_mola.baslangic_saati:
        bas = datetime.datetime.combine(aktif_mola.tarih or today, aktif_mola.baslangic_saati)
        start_iso = bas.strftime('%Y-%m-%dT%H:%M:%S')
        hedef_dk = BIRINCI_MOLA_DK if aktif_mola.mola_tipi == '1. Mola' else kalan_hak
    return {'aktif_mola': aktif_mola, 'kullanilan_dk': kullanilan, 'kalan_hak': kalan_hak,
            'gunluk_hak': GUNLUK_TOPLAM_MOLA_DK, 'start_iso': start_iso, 'hedef_dk': hedef_dk,
            'bugun_biten_sayi': bugun_biten.count()}


# =========================================================================
# PERSONEL ANA SAYFA (mola + vardiyalarım)
# =========================================================================
def _personel_home(request, personel):
    today = timezone.localdate()
    if request.method == 'POST' and request.POST.get('islem') == 'mola_toggle':
        _mola_toggle(request, personel)
        return redirect('ana_sayfa')

    start, end, gunler = _hafta_gunleri('bu')
    vmap = {v.tarih: v for v in personel.vardiyalar.filter(tarih__range=[start, end], durum=OnayDurumu.ONAYLANDI)}
    hafta = [{'tarih': g, 'gun_adi': GUN_ADLARI[i], 'bugun': g == today, 'vardiya': vmap.get(g)}
             for i, g in enumerate(gunler)]
    g_start, g_end, g_gunler = _hafta_gunleri('gelecek')
    g_vmap = {v.tarih: v for v in personel.vardiyalar.filter(tarih__range=[g_start, g_end], durum=OnayDurumu.ONAYLANDI)}
    gelecek = [{'tarih': g, 'gun_adi': GUN_ADLARI[i], 'bugun': False, 'vardiya': g_vmap.get(g)}
               for i, g in enumerate(g_gunler)]
    ctx = {'personel': personel, 'aktif': 'home', 'is_gm': False,
           'hafta': hafta, 'haftabasi': start, 'haftasonu': end,
           'gelecek': gelecek, 'g_basi': g_start, 'g_sonu': g_end}
    ctx.update(_mola_ctx(personel, today))
    return render(request, 'personel_panel.html', ctx)


# =========================================================================
# ŞEF ANA SAYFA (vardiya planı + personel)
# =========================================================================
def _sef_home(request, personel):
    sube = personel.sube
    secili = request.GET.get('hafta', 'gelecek')
    if secili not in ('bu', 'gelecek'):
        secili = 'gelecek'
    start, end, gunler = _hafta_gunleri(secili)

    if request.method == 'POST':
        islem = request.POST.get('islem')
        if islem == 'mola_toggle':
            _mola_toggle(request, personel)
            return redirect(f'/?hafta={secili}')
        if not sube:
            messages.error(request, "Şubeniz tanımlı değil. Yöneticinize başvurun.")
            return redirect('ana_sayfa')
        if islem == 'vardiya_kaydet':
            _vardiya_kaydet(request, sube)
            return redirect(f'/?hafta={secili}')
        if islem == 'onaya_gonder':
            Vardiya.objects.filter(personel__sube=sube, tarih__range=[start, end],
                                   durum__in=[OnayDurumu.TASLAK, OnayDurumu.REDDEDILDI]
                                   ).update(durum=OnayDurumu.ONAY_BEKLIYOR, red_notu=None)
            messages.success(request, "Vardiya programı yönetici onayına gönderildi.")
            return redirect(f'/?hafta={secili}')
        if islem == 'personel_ekle':
            ad = request.POST.get('ad_soyad', '').strip()
            if ad:
                yeni = Personel.objects.create(ad_soyad=ad, sube=sube, rol=Rol.PERSONEL)
                messages.success(request, f"{yeni.ad_soyad} eklendi. Giriş kodu: {yeni.giris_kodu}")
            else:
                messages.error(request, "Ad soyad boş olamaz.")
            return redirect(f'/?hafta={secili}')
        if islem == 'personel_cikar':
            Personel.objects.filter(id=request.POST.get('personel_id'), sube=sube, rol=Rol.PERSONEL).delete()
            messages.success(request, "Personel şubeden çıkarıldı.")
            return redirect(f'/?hafta={secili}')

    personeller = list(sube.personeller.order_by('ad_soyad')) if sube else []
    tablo = _vardiya_tablo(personeller, start, end, gunler)
    ctx = {'personel': personel, 'aktif': 'home', 'is_gm': False, 'sube': sube,
           'vardiya_tipleri': VardiyaTipi.choices, 'secili': secili,
           'haftabasi': start, 'haftasonu': end, 'personeller': personeller}
    ctx.update(tablo)
    ctx.update(_mola_ctx(personel, timezone.localdate()))
    return render(request, 'sef_panel.html', ctx)


def _vardiya_kaydet(request, sube):
    """Ortak: bir hücreyi kaydet/sil. Yalnızca verilen şubedeki personel için."""
    pid = request.POST.get('target_personel_id')
    tarih_str = request.POST.get('vardiya_tarihi', '')
    tip = request.POST.get('vardiya_tipi', '')
    try:
        t = datetime.datetime.strptime(tarih_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Geçersiz tarih.")
        return
    hedef = Personel.objects.filter(id=pid, sube=sube).first()
    if not hedef:
        messages.error(request, "Yetkisiz işlem.")
        return
    if tip == 'Sil':
        Vardiya.objects.filter(personel=hedef, tarih=t).delete()
    elif tip in VardiyaTipi.values:
        Vardiya.objects.update_or_create(
            personel=hedef, tarih=t,
            defaults={'vardiya_tipi': tip, 'durum': OnayDurumu.TASLAK, 'red_notu': None})


# =========================================================================
# YÖNETİCİ — VARDİYA ( / )
# =========================================================================
def _yonetici_vardiya(request, personel):
    is_gm = personel.rol == Rol.GENEL_MUDUR
    subeler = _yon_subeler(personel)
    sel_sube = _yonetici_sube(request, subeler)
    secili = request.GET.get('hafta', 'gelecek')
    if secili not in ('bu', 'gelecek'):
        secili = 'gelecek'
    start, end, gunler = _hafta_gunleri(secili)

    if request.method == 'POST' and sel_sube:
        islem = request.POST.get('islem')
        if islem == 'vardiya_kaydet':
            _vardiya_kaydet(request, sel_sube)
        elif islem == 'plan_onayla':
            Vardiya.objects.filter(personel__sube=sel_sube, tarih__range=[start, end],
                                   durum=OnayDurumu.ONAY_BEKLIYOR).update(durum=OnayDurumu.ONAYLANDI, red_notu=None)
            messages.success(request, "Vardiya planı onaylandı.")
        elif islem == 'plan_reddet':
            neden = request.POST.get('red_notu', '').strip() or 'Neden belirtilmedi.'
            Vardiya.objects.filter(personel__sube=sel_sube, tarih__range=[start, end],
                                   durum=OnayDurumu.ONAY_BEKLIYOR).update(durum=OnayDurumu.REDDEDILDI, red_notu=neden)
            messages.success(request, "Vardiya planı reddedildi ve şefe geri gönderildi.")
        return redirect(f'/?hafta={secili}')

    personeller = list(sel_sube.personeller.order_by('ad_soyad')) if sel_sube else []
    tablo = _vardiya_tablo(personeller, start, end, gunler)
    ctx = {'personel': personel, 'aktif': 'home', 'is_gm': is_gm, 'subeler': subeler, 'sel_sube': sel_sube,
           'vardiya_tipleri': VardiyaTipi.choices, 'secili': secili, 'haftabasi': start, 'haftasonu': end}
    ctx.update(tablo)
    return render(request, 'yonetici_vardiya.html', ctx)


# =========================================================================
# PUANTAJ SAYFASI ( /puantaj/ ) — şef (kendi şubesi) + üst yönetim
# =========================================================================
def puantaj_sayfa(request):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    if _cikis_mi(request):
        return _logout(request)
    personel = _aktif_personel(request)
    if personel is None or personel.rol == Rol.PERSONEL:
        return redirect('ana_sayfa')

    is_gm = personel.rol == Rol.GENEL_MUDUR
    is_yon = personel.rol in UST_YONETIM
    subeler = _yon_subeler(personel) if is_yon else []
    sel_sube = _yonetici_sube(request, subeler) if is_yon else personel.sube
    ay_str = request.GET.get('puantaj_ay') or timezone.localdate().strftime('%Y-%m')
    ay_ilk, ay_son = _ay_araligi(ay_str)

    if request.method == 'POST' and sel_sube:
        islem = request.POST.get('islem')
        hedef = Personel.objects.filter(id=request.POST.get('target_personel_id'), sube=sel_sube).first()
        if hedef and islem == 'puantaj_kaydet':
            def _say(ad):
                try:
                    return max(0, int(request.POST.get(ad, 0)))
                except (TypeError, ValueError):
                    return 0
            Puantaj.objects.update_or_create(
                personel=hedef, ay=ay_ilk,
                defaults={'calisilan_gun': _say('calisilan_gun'), 'eksik_gun': _say('eksik_gun'),
                          'izinli_gun': _say('izinli_gun'), 'raporlu_gun': _say('raporlu_gun'),
                          'manuel_duzenlendi': True})
            messages.success(request, f"{hedef.ad_soyad} puantajı elle güncellendi.")
        elif hedef and islem == 'puantaj_sifirla':
            Puantaj.objects.filter(personel=hedef, ay=ay_ilk).delete()
            messages.success(request, "Puantaj otomatik hesaplamaya döndürüldü.")
        return redirect(f'/puantaj/?puantaj_ay={ay_str}')

    personeller = list(sel_sube.personeller.order_by('ad_soyad')) if sel_sube else []
    aralik = _gun_araligi(request, 'puantaj_bas', 'puantaj_bit')
    aralik_mod = aralik is not None
    if aralik_mod:
        bas, son, bas_str, bit_str = aralik
        hesap_bas, hesap_son, manuel_ay = bas, son, None
    else:
        hesap_bas, hesap_son, manuel_ay = ay_ilk, ay_son, ay_ilk
        bas_str = bit_str = ''

    liste = []
    for p in personeller:
        d = _puantaj_hesapla(p, hesap_bas, hesap_son, manuel_ay=manuel_ay)
        d['personel'] = p
        # Hakediş: yalnızca çalışılan + izinli; raporlu ve eksik (devamsız) yansımaz
        d['hakedis'] = d['calisilan'] + d['izinli']
        liste.append(d)
    return render(request, 'puantaj.html', {
        'personel': personel, 'aktif': 'puantaj', 'is_gm': is_gm, 'is_yon': is_yon,
        'subeler': subeler, 'sel_sube': sel_sube, 'puantaj_listesi': liste,
        'selected_ay_str': ay_str, 'aralik_mod': aralik_mod,
        'puantaj_bas': bas_str, 'puantaj_bit': bit_str,
    })


# =========================================================================
# MOLA SAYFASI ( /mola/ ) — istenilen günün mola süreleri
# =========================================================================
def mola_sayfa(request):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    if _cikis_mi(request):
        return _logout(request)
    personel = _aktif_personel(request)
    if personel is None or personel.rol == Rol.PERSONEL:
        return redirect('ana_sayfa')

    is_gm = personel.rol == Rol.GENEL_MUDUR
    is_yon = personel.rol in UST_YONETIM
    subeler = _yon_subeler(personel) if is_yon else []
    sel_sube = _yonetici_sube(request, subeler) if is_yon else personel.sube

    tarih_str = request.GET.get('mola_tarih')
    try:
        ref = datetime.datetime.strptime(tarih_str, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        ref = timezone.localdate()

    personeller = list(sel_sube.personeller.order_by('ad_soyad')) if sel_sube else []
    molalar = (list(Mola.objects.filter(personel__in=personeller, tarih=ref, bitis_saati__isnull=False)
                    .order_by('baslangic_saati')) if personeller else [])
    gun_rapor = []
    for p in personeller:
        kayit = [m for m in molalar if m.personel_id == p.id]
        toplam = sum(m.mola_suresi_dakika() for m in kayit)
        gun_rapor.append({'personel': p, 'molalar': kayit, 'toplam': toplam,
                          'asildi': toplam > MOLA_LIMIT_UYARI_DK})
    return render(request, 'mola.html', {
        'personel': personel, 'aktif': 'mola', 'is_gm': is_gm, 'is_yon': is_yon,
        'subeler': subeler, 'sel_sube': sel_sube, 'gun_rapor': gun_rapor,
        'secili_tarih': ref.strftime('%Y-%m-%d'), 'mola_limit': MOLA_LIMIT_UYARI_DK,
    })


# =========================================================================
# EKİP YÖNETİMİ ( /ekip/ ) — üst yönetim
# =========================================================================
def _kullanici_adi_uret(ad):
    t = ad.lower().strip()
    for k, v in {'ı': 'i', 'ş': 's', 'ğ': 'g', 'ü': 'u', 'ö': 'o', 'ç': 'c', 'İ': 'i'}.items():
        t = t.replace(k, v)
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode()
    t = '.'.join(t.split())
    base = ''.join(ch for ch in t if ch.isalnum() or ch == '.') or 'kullanici'
    uname, i = base, 1
    while User.objects.filter(username=uname).exists():
        i += 1
        uname = f"{base}{i}"
    return uname


def _yeni_sifre():
    return secrets.token_urlsafe(6)


def ekip_sayfa(request):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    if _cikis_mi(request):
        return _logout(request)
    personel = _aktif_personel(request)
    if personel is None or personel.rol not in UST_YONETIM:
        return redirect('ana_sayfa')

    subeler = _yon_subeler(personel)
    is_tam = personel.rol in TAM_YETKILI
    if request.method == 'POST':
        if not is_tam:
            return redirect('ekip')
        islem = request.POST.get('islem')

        if islem == 'yonetici_ekle':
            ad = request.POST.get('ad_soyad', '').strip()
            rol = request.POST.get('rol', '')
            if ad and rol in OFIS_ROLLERI:
                uname = _kullanici_adi_uret(ad)
                sifre = _yeni_sifre()
                u = User.objects.create(username=uname)
                u.set_password(sifre)
                u.save()
                Personel.objects.create(user=u, ad_soyad=ad, rol=rol)
                messages.success(request, f"{ad} ({rol}) eklendi. Kullanıcı adı: {uname} · Şifre: {sifre} — bu şifre yalnızca şimdi görünür, not alın.")
            else:
                messages.error(request, "Ad soyad ve geçerli bir yönetici rolü zorunlu.")
            return redirect('ekip')

        if islem == 'yonetici_sifre_yenile':
            s = Personel.objects.filter(id=request.POST.get('personel_id'), rol__in=OFIS_ROLLERI).select_related('user').first()
            if s and s.user:
                sifre = _yeni_sifre()
                s.user.set_password(sifre)
                s.user.save()
                messages.success(request, f"{s.ad_soyad} için yeni şifre: {sifre} · Kullanıcı adı: {s.user.username} — şimdi not alın.")
            return redirect('ekip')

        if islem == 'yonetici_cikar':
            s = Personel.objects.filter(id=request.POST.get('personel_id'), rol__in=OFIS_ROLLERI).select_related('user').first()
            if s and s.id == personel.id:
                messages.error(request, "Kendi hesabınızı buradan çıkaramazsınız.")
            elif s:
                (s.user or s).delete()
                messages.success(request, "Yönetici hesabı çıkarıldı.")
            return redirect('ekip')

        if islem == 'bolge_sube_ata':
            m = Personel.objects.filter(id=request.POST.get('mudur_id'), rol=Rol.MUDUR).first()
            if m:
                ids = request.POST.getlist('sube_idler')
                m.sorumlu_subeler.set(Sube.objects.filter(id__in=ids))
                messages.success(request, f"{m.ad_soyad} için sorumlu şubeler güncellendi ({m.sorumlu_subeler.count()} şube).")
            return redirect('ekip')

        if islem == 'sef_ekle':
            ad = request.POST.get('ad_soyad', '').strip()
            sid = request.POST.get('sef_sube_id')
            if ad and sid:
                yeni = Personel.objects.create(ad_soyad=ad, sube_id=sid, rol=Rol.SEF)
                messages.success(request, f"{ad} şef olarak eklendi. Giriş kodu: {yeni.giris_kodu} (şef de kodla girer).")
            else:
                messages.error(request, "Ad soyad ve şube zorunlu.")
            return redirect('ekip')

        if islem == 'sef_cikar':
            s = Personel.objects.filter(id=request.POST.get('sef_id'), rol=Rol.SEF).select_related('user').first()
            if s:
                (s.user or s).delete()
                messages.success(request, "Şef sistemden çıkarıldı.")
            return redirect('ekip')

        if islem == 'sef_degistir':
            s = Personel.objects.filter(id=request.POST.get('sef_id'), rol=Rol.SEF).first()
            if s:
                ad = request.POST.get('yeni_ad_soyad', '').strip()
                sb = request.POST.get('yeni_sube_id')
                if ad:
                    s.ad_soyad = ad
                if sb:
                    s.sube_id = sb
                s.save()
                messages.success(request, "Şef bilgileri güncellendi.")
            return redirect('ekip')

        if islem == 'egitmen_ekle':
            s = Personel.objects.filter(id=request.POST.get('personel_id'),
                                        rol__in=[Rol.PERSONEL, Rol.SEF]).first()
            if s:
                s.egitmen = True
                s.save(update_fields=['egitmen'])
                messages.success(request, f"{s.ad_soyad} artık eğitmen (kodla girip soru yönetimine erişir).")
            return redirect('ekip')

        if islem == 'egitmen_cikar':
            s = Personel.objects.filter(id=request.POST.get('personel_id')).first()
            if s:
                s.egitmen = False
                s.save(update_fields=['egitmen'])
                messages.success(request, f"{s.ad_soyad} eğitmen yetkisinden çıkarıldı.")
            return redirect('ekip')

    yoneticiler = list(Personel.objects.filter(rol__in=OFIS_ROLLERI).select_related('user').order_by('ad_soyad'))
    sefler_qs = Personel.objects.filter(rol=Rol.SEF).select_related('sube')
    if personel.rol == Rol.MUDUR:
        sefler_qs = sefler_qs.filter(sube_id__in=[s.id for s in subeler])
    sefler = list(sefler_qs.order_by('ad_soyad'))

    is_atayabilir = is_tam
    bolge_mudurleri = []
    tum_subeler = []
    egitmenler = []
    egitmen_adaylari = []
    if is_atayabilir:
        tum_subeler = list(Sube.objects.order_by('ad'))
        bolge_mudurleri = list(Personel.objects.filter(rol=Rol.MUDUR)
                               .prefetch_related('sorumlu_subeler').order_by('ad_soyad'))
        for m in bolge_mudurleri:
            m.atanan_ids = set(m.sorumlu_subeler.values_list('id', flat=True))
        egitmenler = list(Personel.objects.filter(egitmen=True)
                          .select_related('sube').order_by('ad_soyad'))
        egitmen_adaylari = list(Personel.objects.filter(rol__in=[Rol.PERSONEL, Rol.SEF], egitmen=False)
                                .select_related('sube').order_by('ad_soyad'))
    return render(request, 'ekip.html', {
        'personel': personel, 'aktif': 'ekip', 'subeler': subeler,
        'yoneticiler': yoneticiler, 'sefler': sefler,
        'yonetici_rolleri': OFIS_ROLLERI,
        'is_tam': is_tam,
        'is_atayabilir': is_atayabilir, 'bolge_mudurleri': bolge_mudurleri, 'tum_subeler': tum_subeler,
        'egitmenler': egitmenler, 'egitmen_adaylari': egitmen_adaylari,
    })


# =========================================================================
# EXCEL — Puantaj
# =========================================================================
def puantaj_excel_export(request):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    p = _aktif_personel(request)
    if not p or p.rol == Rol.PERSONEL:
        return redirect('ana_sayfa')
    ay_str = request.GET.get('puantaj_ay') or timezone.localdate().strftime('%Y-%m')
    ay_ilk, ay_son = _ay_araligi(ay_str)
    aralik = _gun_araligi(request, 'puantaj_bas', 'puantaj_bit')
    if aralik:
        hbas, hson, bas_str, bit_str = aralik
        manuel_ay = None
        donem_etiket = f"{bas_str} – {bit_str}"
    else:
        hbas, hson, manuel_ay = ay_ilk, ay_son, ay_ilk
        donem_etiket = ay_str
    if p.rol == Rol.SEF:
        subeler = Sube.objects.filter(id=p.sube_id) if p.sube_id else Sube.objects.none()
    else:
        sid = request.GET.get('sube_id') or request.session.get('sel_sube_id')
        izinli = _yon_subeler(p)
        izinli_ids = [s.id for s in izinli]
        if sid and (int(sid) in izinli_ids if str(sid).isdigit() else False):
            subeler = Sube.objects.filter(id=sid)
        else:
            subeler = Sube.objects.filter(id__in=izinli_ids).order_by('ad')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Puantaj"
    navy = PatternFill("solid", fgColor="162AA3")
    branch_fill = PatternFill("solid", fgColor="E1E8F0")
    head_font = Font(size=10, bold=True, color="FFFFFF")
    branch_font = Font(size=11, bold=True, color="162AA3")
    bold = Font(size=10, bold=True)
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")
    thin = Side(border_style="thin", color="DDDDDD")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.merge_cells("A1:H1")
    ws["A1"] = f"GEEK PANEL — Puantaj ({donem_etiket})"
    ws["A1"].font = Font(size=14, bold=True, color="162AA3")
    basliklar = ["Ad Soyad", "Görev", "Çalışılan", "Eksik (Devamsız)", "İzinli", "Raporlu", "Hakediş", "Kaynak"]
    for c, t in enumerate(basliklar, 1):
        cell = ws.cell(row=3, column=c, value=t)
        cell.font = head_font
        cell.fill = navy
        cell.alignment = center
        cell.border = border
    r = 4
    for s in subeler:
        plist = Personel.objects.filter(sube=s).order_by('ad_soyad')
        if not plist.exists():
            continue
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
        bc = ws.cell(row=r, column=1, value=f"Şube: {s.ad}")
        bc.font = branch_font
        bc.alignment = left
        for c in range(1, 9):
            ws.cell(row=r, column=c).fill = branch_fill
            ws.cell(row=r, column=c).border = border
        r += 1
        bas = r
        for pp in plist:
            d = _puantaj_hesapla(pp, hbas, hson, manuel_ay=manuel_ay)
            ws.cell(row=r, column=1, value=pp.ad_soyad).alignment = left
            ws.cell(row=r, column=2, value=pp.rol).alignment = center
            ws.cell(row=r, column=3, value=d['calisilan']).alignment = center
            ws.cell(row=r, column=4, value=d['eksik']).alignment = center
            ws.cell(row=r, column=5, value=d['izinli']).alignment = center
            ws.cell(row=r, column=6, value=d['raporlu']).alignment = center
            hc = ws.cell(row=r, column=7, value=f"=C{r}+E{r}")
            hc.alignment = center
            hc.font = bold
            ws.cell(row=r, column=8, value="Manuel" if d['manuel'] else "Otomatik").alignment = center
            for c in range(1, 9):
                ws.cell(row=r, column=c).border = border
            r += 1
        son = r - 1
        ws.cell(row=r, column=1, value=f"{s.ad} Toplam").font = bold
        for c in range(3, 8):
            L = get_column_letter(c)
            tc = ws.cell(row=r, column=c, value=f"=SUM({L}{bas}:{L}{son})")
            tc.font = bold
            tc.alignment = center
        for c in range(1, 9):
            ws.cell(row=r, column=c).border = border
        r += 2
    for i, c in enumerate(basliklar, 1):
        ws.column_dimensions[get_column_letter(i)].width = max(12, len(c) + 4)

    resp = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = f'attachment; filename="GeekPanel_Puantaj_{ay_str}.xlsx"'
    wb.save(resp)
    return resp


# =========================================================================
# ZAYİ ( /zayi/ ) — personel/şef girer, üst yönetim görüntüler
# =========================================================================
def zayi_sayfa(request):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    if _cikis_mi(request):
        return _logout(request)
    personel = _aktif_personel(request)
    if personel is None:
        return redirect('ana_sayfa')

    ekleyebilir = personel.rol in (Rol.PERSONEL, Rol.SEF)
    is_yon = personel.rol in UST_YONETIM
    subeler = _yon_subeler(personel) if is_yon else []
    sel_sube = _yonetici_sube(request, subeler) if is_yon else personel.sube
    ay_str = request.GET.get('zayi_ay') or timezone.localdate().strftime('%Y-%m')
    ay_ilk, ay_son = _ay_araligi(ay_str)

    if request.method == 'POST' and ekleyebilir:
        if not sel_sube:
            messages.error(request, "Şubeniz tanımlı değil. Yöneticinize başvurun.")
            return redirect('zayi')
        islem = request.POST.get('islem')
        if islem == 'zayi_ekle':
            urun = request.POST.get('urun_adi', '').strip()
            birim = request.POST.get('birim', '')
            try:
                miktar = Decimal(request.POST.get('miktar', '').replace(',', '.'))
            except (InvalidOperation, AttributeError):
                miktar = None
            if urun and birim in [Birim.ADET, Birim.ML] and miktar is not None and miktar > 0:
                Zayi.objects.create(sube=sel_sube, giren=personel, giren_ad=personel.ad_soyad,
                                    urun_adi=urun, miktar=miktar, birim=birim)
                messages.success(request, f"{urun} ({miktar:g} {birim}) zayi olarak kaydedildi.")
            else:
                messages.error(request, "Ürün adı, geçerli bir miktar ve birim gerekli.")
        elif personel.rol == Rol.SEF and islem in ('zayi_duzenle', 'zayi_sil'):
            z = Zayi.objects.filter(id=request.POST.get('zayi_id'), sube=sel_sube).first()
            bugun_mu = z and timezone.localtime(z.olusturma).date() == timezone.localdate()
            if not z or not bugun_mu:
                messages.error(request, "Yalnızca bugün girilen kayıtlar düzenlenebilir.")
            elif islem == 'zayi_sil':
                z.delete()
                messages.success(request, "Zayi kaydı silindi.")
            else:
                urun = request.POST.get('urun_adi', '').strip()
                birim = request.POST.get('birim', '')
                try:
                    miktar = Decimal(request.POST.get('miktar', '').replace(',', '.'))
                except (InvalidOperation, AttributeError):
                    miktar = None
                if urun and birim in [Birim.ADET, Birim.ML] and miktar is not None and miktar > 0:
                    z.urun_adi, z.miktar, z.birim = urun, miktar, birim
                    z.save()
                    messages.success(request, "Zayi kaydı güncellendi.")
                else:
                    messages.error(request, "Ürün adı, geçerli bir miktar ve birim gerekli.")
        return redirect('zayi')

    kayitlar, grafik = [], None
    aralik = _gun_araligi(request, 'zayi_bas', 'zayi_bit')
    aralik_mod = aralik is not None
    if aralik_mod:
        bas, son, bas_str, bit_str = aralik
    else:
        bas, son = ay_ilk, ay_son
        bas_str = bit_str = ''
    if sel_sube:
        kayitlar = list(Zayi.objects.filter(sube=sel_sube, olusturma__date__gte=bas,
                                            olusturma__date__lt=son).select_related('giren'))
        if personel.rol == Rol.SEF:
            bugun = timezone.localdate()
            for z in kayitlar:
                z.duzenlenebilir = timezone.localtime(z.olusturma).date() == bugun
        if is_yon:
            agg = list(Zayi.objects.filter(sube=sel_sube, olusturma__date__gte=bas, olusturma__date__lt=son)
                       .values('urun_adi', 'birim').annotate(toplam=Sum('miktar')).order_by('-toplam'))
            maxv = max((float(a['toplam']) for a in agg), default=0)
            toplam_genel = sum(float(a['toplam']) for a in agg)
            grafik = [{'urun': a['urun_adi'], 'birim': a['birim'], 'toplam': a['toplam'],
                       'yuzde': round(float(a['toplam']) / maxv * 100, 1) if maxv else 0,
                       'oran': round(float(a['toplam']) / toplam_genel * 100, 1) if toplam_genel else 0}
                      for a in agg]

    return render(request, 'zayi.html', {
        'personel': personel, 'aktif': 'zayi', 'ekleyebilir': ekleyebilir, 'is_yon': is_yon,
        'subeler': subeler, 'sel_sube': sel_sube, 'kayitlar': kayitlar, 'grafik': grafik,
        'selected_ay_str': ay_str, 'birimler': Birim.choices,
        'aralik_mod': aralik_mod, 'zayi_bas': bas_str, 'zayi_bit': bit_str,
    })


def zayi_excel_export(request):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    p = _aktif_personel(request)
    if not p or p.rol not in UST_YONETIM:
        return redirect('ana_sayfa')
    ay_str = request.GET.get('zayi_ay') or timezone.localdate().strftime('%Y-%m')
    ay_ilk, ay_son = _ay_araligi(ay_str)
    aralik = _gun_araligi(request, 'zayi_bas', 'zayi_bit')
    if aralik:
        bas, son, bas_str, bit_str = aralik
        donem_etiket = f"{bas_str} – {bit_str}"
    else:
        bas, son = ay_ilk, ay_son
        donem_etiket = ay_str
    sid = request.GET.get('sube_id') or request.session.get('sel_sube_id')
    sube = Sube.objects.filter(id=sid).first()
    izin_ids = [s.id for s in _yon_subeler(p)] if p.rol == Rol.MUDUR else None
    if izin_ids is not None and sube and sube.id not in izin_ids:
        sube = None
    qs = Zayi.objects.filter(olusturma__date__gte=bas, olusturma__date__lt=son).select_related('sube', 'giren')
    if sube:
        qs = qs.filter(sube=sube)
    elif izin_ids is not None:
        qs = qs.filter(sube_id__in=izin_ids)
    qs = qs.order_by('olusturma')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Zayi"
    navy = PatternFill("solid", fgColor="162AA3")
    head_font = Font(size=10, bold=True, color="FFFFFF")
    bold = Font(size=10, bold=True)
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")
    thin = Side(border_style="thin", color="DDDDDD")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.merge_cells("A1:F1")
    ws["A1"] = f"GEEK PANEL — Zayi Listesi ({donem_etiket}{' · ' + sube.ad if sube else ' · Tüm şubeler'})"
    ws["A1"].font = Font(size=14, bold=True, color="162AA3")
    basliklar = ["Tarih", "Saat", "Şube", "Ürün", "Miktar", "Birim", "Giren"]
    for c, t in enumerate(basliklar, 1):
        cell = ws.cell(row=3, column=c, value=t)
        cell.font = head_font
        cell.fill = navy
        cell.alignment = center
        cell.border = border
    r = 4
    for z in qs:
        yerel = timezone.localtime(z.olusturma)
        ws.cell(row=r, column=1, value=yerel.strftime('%d.%m.%Y')).alignment = center
        ws.cell(row=r, column=2, value=yerel.strftime('%H:%M')).alignment = center
        ws.cell(row=r, column=3, value=z.sube.ad if z.sube else '-').alignment = left
        ws.cell(row=r, column=4, value=z.urun_adi).alignment = left
        ws.cell(row=r, column=5, value=float(z.miktar)).alignment = center
        ws.cell(row=r, column=6, value=z.birim).alignment = center
        ws.cell(row=r, column=7, value=z.giren_ad or '-').alignment = left
        for c in range(1, 8):
            ws.cell(row=r, column=c).border = border
        r += 1
    if r == 4:
        ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=7)
        ws.cell(row=4, column=1, value="Bu ay için kayıt yok.").alignment = center
    widths = [12, 8, 16, 26, 10, 8, 20]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    resp = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = f'attachment; filename="GeekPanel_Zayi_{ay_str}.xlsx"'
    wb.save(resp)
    return resp


# =========================================================================
# KALİBRASYON ( /kalibrasyon/ ) — anlık kamera çekimi, 1 ay saklanır
# =========================================================================
KALIBRASYON_GUN = 31


def _kalibrasyon_temizle():
    """1 aydan eski kalibrasyon kayıtlarını ve dosyalarını siler."""
    sinir = timezone.now() - datetime.timedelta(days=KALIBRASYON_GUN)
    for k in Kalibrasyon.objects.filter(olusturma__lt=sinir):
        if k.foto:
            k.foto.delete(save=False)
        k.delete()


def kalibrasyon_sayfa(request):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    if _cikis_mi(request):
        return _logout(request)
    personel = _aktif_personel(request)
    if personel is None:
        return redirect('ana_sayfa')

    ekleyebilir = personel.rol in (Rol.PERSONEL, Rol.SEF)
    is_yon = personel.rol in UST_YONETIM
    subeler = _yon_subeler(personel) if is_yon else []
    sel_sube = _yonetici_sube(request, subeler) if is_yon else personel.sube

    today = timezone.localdate()
    en_eski = today - datetime.timedelta(days=KALIBRASYON_GUN)
    if is_yon:
        try:
            ref = datetime.datetime.strptime(request.GET.get('kalibrasyon_tarih'), '%Y-%m-%d').date()
        except (TypeError, ValueError):
            ref = today
        ref = min(max(ref, en_eski), today)
    else:
        ref = today

    if request.method == 'POST' and ekleyebilir:
        if not sel_sube:
            messages.error(request, "Şubeniz tanımlı değil. Yöneticinize başvurun.")
            return redirect('kalibrasyon')
        if request.POST.get('islem') == 'kalibrasyon_yukle':
            data = request.POST.get('foto_data', '')
            raw = None
            if data.startswith('data:image'):
                try:
                    raw = base64.b64decode(data.split(',', 1)[1])
                except (ValueError, IndexError):
                    raw = None
            if raw and 100 < len(raw) <= 8 * 1024 * 1024:
                _kalibrasyon_temizle()
                k = Kalibrasyon(sube=sel_sube, giren=personel, giren_ad=personel.ad_soyad)
                fname = f"kal_{sel_sube.id}_{personel.id}_{timezone.now():%Y%m%d_%H%M%S}.jpg"
                k.foto.save(fname, ContentFile(raw), save=True)
                messages.success(request, "Kalibrasyon görüntüsü yüklendi.")
            else:
                messages.error(request, "Görüntü alınamadı. Lütfen kameradan tekrar çekin.")
        return redirect('kalibrasyon')

    gorseller = []
    if sel_sube:
        gorseller = list(Kalibrasyon.objects.filter(sube=sel_sube, olusturma__date=ref).select_related('giren'))

    return render(request, 'kalibrasyon.html', {
        'personel': personel, 'aktif': 'kalibrasyon', 'ekleyebilir': ekleyebilir, 'is_yon': is_yon,
        'subeler': subeler, 'sel_sube': sel_sube, 'gorseller': gorseller,
        'secili_tarih': ref.strftime('%Y-%m-%d'), 'en_eski_tarih': en_eski.strftime('%Y-%m-%d'),
        'bugun': today.strftime('%Y-%m-%d'), 'saklama_gun': KALIBRASYON_GUN,
    })


# =========================================================================
# İRSALİYE / ÜRÜN TRANSFER ( /irsaliye/ ) — sevkiyatçı yükler, yönetim görüntüler
# =========================================================================
IRSALIYE_GUN = 180  # 6 ay


def _irsaliye_temizle():
    """6 aydan eski irsaliye kayıtlarını ve dosyalarını siler."""
    sinir = timezone.now() - datetime.timedelta(days=IRSALIYE_GUN)
    for k in Irsaliye.objects.filter(olusturma__lt=sinir):
        if k.foto:
            k.foto.delete(save=False)
        k.delete()


def irsaliye_sayfa(request):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    if _cikis_mi(request):
        return _logout(request)
    personel = _aktif_personel(request)
    if personel is None:
        return redirect('ana_sayfa')

    ekleyebilir = personel.rol == Rol.SEVKIYAT
    goruntuleyebilir = personel.rol in (Rol.SATIN_ALMA, Rol.GENEL_MUDUR, Rol.MUDUR, Rol.OPERATOR, Rol.YATIRIMCI)
    if not (ekleyebilir or goruntuleyebilir):
        return redirect('ana_sayfa')

    today = timezone.localdate()
    en_eski = today - datetime.timedelta(days=IRSALIYE_GUN)
    if goruntuleyebilir:
        try:
            ref = datetime.datetime.strptime(request.GET.get('irsaliye_tarih'), '%Y-%m-%d').date()
        except (TypeError, ValueError):
            ref = today
        ref = min(max(ref, en_eski), today)
    else:
        ref = today

    if request.method == 'POST' and ekleyebilir:
        if request.POST.get('islem') == 'irsaliye_yukle':
            data = request.POST.get('foto_data', '')
            aciklama = request.POST.get('aciklama', '').strip()
            raw = None
            if data.startswith('data:image'):
                try:
                    raw = base64.b64decode(data.split(',', 1)[1])
                except (ValueError, IndexError):
                    raw = None
            if not aciklama:
                messages.error(request, "Açıklama zorunlu. Lütfen transfer bilgisini yazın.")
            elif raw and 100 < len(raw) <= 8 * 1024 * 1024:
                _irsaliye_temizle()
                k = Irsaliye(giren=personel, giren_ad=personel.ad_soyad, aciklama=aciklama)
                fname = f"irs_{personel.id}_{timezone.now():%Y%m%d_%H%M%S}.jpg"
                k.foto.save(fname, ContentFile(raw), save=True)
                messages.success(request, "İrsaliye görüntüsü yüklendi.")
            else:
                messages.error(request, "Görüntü alınamadı. Lütfen kameradan tekrar çekin.")
        return redirect('irsaliye')

    kayitlar = list(Irsaliye.objects.filter(olusturma__date=ref).select_related('giren'))
    return render(request, 'irsaliye.html', {
        'personel': personel, 'aktif': 'irsaliye', 'ekleyebilir': ekleyebilir,
        'goruntuleyebilir': goruntuleyebilir, 'kayitlar': kayitlar,
        'secili_tarih': ref.strftime('%Y-%m-%d'), 'en_eski_tarih': en_eski.strftime('%Y-%m-%d'),
        'bugun': today.strftime('%Y-%m-%d'),
    })


# =========================================================================
# STOK SAYIMI ( /stok/ ) — şube şefi ay sonu stok girer; yönetim şube bazında görür
# =========================================================================
def stok_sayimi(request):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    if _cikis_mi(request):
        return _logout(request)
    personel = _aktif_personel(request)
    if personel is None:
        return redirect('ana_sayfa')

    is_sef = personel.rol == Rol.SEF
    is_viewer = personel.rol in (Rol.MUDUR, Rol.GENEL_MUDUR, Rol.SATIN_ALMA, Rol.OPERATOR, Rol.YATIRIMCI)
    if not (is_sef or is_viewer):
        return redirect('ana_sayfa')

    ay_str = request.GET.get('stok_ay') or timezone.localdate().strftime('%Y-%m')
    ay_ilk, _ = _ay_araligi(ay_str)

    if is_sef:
        subeler = []
        sel_sube = personel.sube
    else:
        subeler = _yon_subeler(personel)
        sel_sube = _yonetici_sube(request, subeler)

    if request.method == 'POST' and is_sef and sel_sube:
        if request.POST.get('islem') == 'stok_kaydet':
            sayim, _olusan = StokSayim.objects.get_or_create(sube=sel_sube, ay=ay_ilk)
            sayim.giren = personel
            sayim.giren_ad = personel.ad_soyad
            sayim.save()
            sayim.kalemler.all().delete()
            def _say(v):
                try:
                    return Decimal((v or '').strip().replace(',', '.') or '0')
                except Exception:
                    return Decimal('0')
            for u in StokUrun.objects.filter(aktif=True):
                kap = _say(request.POST.get('kapali_%s' % u.id))
                ack = _say(request.POST.get('acik_%s' % u.id))
                note = (request.POST.get('aciklama_%s' % u.id) or '').strip()[:300]
                if kap == 0 and ack == 0 and not note:
                    continue
                StokSayimKalem.objects.create(
                    sayim=sayim, urun=u, urun_ad=u.ad, kategori=u.kategori,
                    kapali_icerik=u.kapali_icerik, acik_carpan=u.acik_carpan,
                    kapali_adet=kap, acik_miktar=ack, aciklama=note)
            # Şefin eklediği, katalogda olmayan ürünler
            ek_adlar = request.POST.getlist('ek_ad')
            ek_miktarlar = request.POST.getlist('ek_miktar')
            ek_notlar = request.POST.getlist('ek_not')
            for idx, ad in enumerate(ek_adlar):
                ad = (ad or '').strip()
                if not ad:
                    continue
                mik = _say(ek_miktarlar[idx]) if idx < len(ek_miktarlar) else Decimal('0')
                note = (ek_notlar[idx].strip()[:300] if idx < len(ek_notlar) else '')
                StokSayimKalem.objects.create(
                    sayim=sayim, urun=None, urun_ad=ad[:200], kategori='EK ÜRÜNLER',
                    kapali_icerik=1, acik_carpan=1, kapali_adet=mik, acik_miktar=0, aciklama=note)
            messages.success(request, f"{ay_ilk:%m.%Y} stok sayımı kaydedildi.")
        return redirect(f"{reverse('stok')}?stok_ay={ay_str}")

    sayim = StokSayim.objects.filter(sube=sel_sube, ay=ay_ilk).first() if sel_sube else None
    girilen = {}
    ek_kalemler = []
    if sayim:
        for k in sayim.kalemler.all():
            if k.urun_id:
                girilen[k.urun_id] = k
            else:
                ek_kalemler.append(k)

    gruplar = []
    if is_sef:
        kat_map = {}
        for u in StokUrun.objects.filter(aktif=True).order_by('sira', 'ad'):
            g = girilen.get(u.id)
            kat_map.setdefault(u.kategori or 'Diğer', []).append({
                'urun': u,
                'kapali': (g.kapali_adet if g else None),
                'acik': (g.acik_miktar if g else None),
                'aciklama': (g.aciklama if g else ''),
            })
        gruplar = [{'kategori': k, 'urunler': v} for k, v in kat_map.items()]
    elif sayim:
        kat_map = {}
        for k in sayim.kalemler.all():
            kat_map.setdefault(k.kategori or 'Diğer', []).append(k)
        gruplar = [{'kategori': k, 'urunler': v} for k, v in kat_map.items()]

    return render(request, 'stok.html', {
        'personel': personel, 'aktif': 'stok', 'is_sef': is_sef, 'is_viewer': is_viewer,
        'subeler': subeler, 'sel_sube': sel_sube, 'gruplar': gruplar, 'sayim': sayim,
        'ek_kalemler': ek_kalemler,
        'selected_ay_str': ay_str,
        'katalog_var': StokUrun.objects.filter(aktif=True).exists(),
    })


def stok_excel(request):
    """Seçili şube + ayın dolu stok sayımını Excel olarak indirir (yükleme şablonu düzeninde)."""
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    personel = _aktif_personel(request)
    if personel is None:
        return redirect('ana_sayfa')
    rol = personel.rol
    if rol not in (Rol.SEF, Rol.MUDUR, Rol.GENEL_MUDUR, Rol.SATIN_ALMA, Rol.OPERATOR, Rol.YATIRIMCI):
        return redirect('ana_sayfa')

    ay_str = request.GET.get('stok_ay') or timezone.localdate().strftime('%Y-%m')
    ay_ilk, _ = _ay_araligi(ay_str)
    sid = request.GET.get('sube_id') or request.session.get('sel_sube_id')
    if rol == Rol.SEF:
        sube = personel.sube
    else:
        sube = Sube.objects.filter(id=sid).first()
        if rol == Rol.MUDUR:
            izin_ids = [s.id for s in _yon_subeler(personel)]
            if not sube or sube.id not in izin_ids:
                return redirect('stok')
    if not sube:
        return redirect('stok')

    sayim = StokSayim.objects.filter(sube=sube, ay=ay_ilk).first()
    kalemler = list(sayim.kalemler.all()) if sayim else []

    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sayım Raporu"
    navy = PatternFill("solid", fgColor="162AA3")
    gray = PatternFill("solid", fgColor="EEF1FB")
    wf = Font(bold=True, color="FFFFFF", name="Arial")
    bf = Font(bold=True, name="Arial")
    nf = Font(name="Arial")
    ctr = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center")
    thin = Side(style="thin", color="C9CEE8")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.merge_cells("A1:H1")
    ws["A1"] = f"GEEK COFFEE SHOP — AYLIK SAYIM RAPORU"
    ws["A1"].font = Font(bold=True, size=13, name="Arial")
    ws["A1"].alignment = ctr
    ws["A2"] = "TARİH:"; ws["B2"] = ay_ilk.strftime("%m.%Y")
    ws["D2"] = "ŞUBE:"; ws["E2"] = sube.ad
    for c in ("A2", "D2"):
        ws[c].font = bf
    # Başlıklar
    ws.merge_cells("C3:D3"); ws["C3"] = "KAPALI KUTU"
    ws.merge_cells("E3:F3"); ws["E3"] = "AÇIK KUTU"
    hdr = ["GRUP", "ÜRÜN ADI", "MİKTAR", "ADET/ML/KG", "MİKTAR", "ADET/ML/KG", "TOPLAM", "AÇIKLAMA"]
    for j, h in enumerate(hdr, 1):
        cell = ws.cell(row=4, column=j, value=h)
        cell.font = wf; cell.fill = navy; cell.alignment = ctr; cell.border = border
    for c in ("C3", "E3"):
        ws[c].font = wf; ws[c].fill = navy; ws[c].alignment = ctr
        ws[c].border = border

    # Veri: katalog sırasına göre tüm kalemler (girilmeyenler boş)
    girilen = {k.urun_ad: k for k in kalemler if k.urun_id}
    ekler = [k for k in kalemler if not k.urun_id]  # şefin eklediği listede olmayan ürünler

    def _yaz(r, kategori, ad, kap, ic, ack, carp, note):
        ws.cell(row=r, column=1, value=kategori).font = nf
        ws.cell(row=r, column=2, value=ad).font = nf
        ws.cell(row=r, column=3, value=(float(kap) if kap is not None else None)).font = nf
        ws.cell(row=r, column=4, value=float(ic)).font = nf
        ws.cell(row=r, column=5, value=(float(ack) if ack is not None else None)).font = nf
        ws.cell(row=r, column=6, value=float(carp)).font = nf
        # TOPLAM: formül yerine hesaplanmış SAYI yazılır (her görüntüleyicide doğru görünür)
        toplam = float((kap or 0)) * float(ic) + float((ack or 0)) * float(carp)
        ws.cell(row=r, column=7, value=toplam).font = bf
        ws.cell(row=r, column=8, value=note).font = nf
        for j in range(1, 9):
            ws.cell(row=r, column=j).border = border
            if j != 2 and j != 8:
                ws.cell(row=r, column=j).alignment = ctr
        if r % 2 == 0:
            for j in range(1, 9):
                ws.cell(row=r, column=j).fill = gray

    r = 5
    for u in StokUrun.objects.filter(aktif=True).order_by('sira', 'ad'):
        k = girilen.get(u.ad)
        _yaz(r, u.kategori, u.ad,
             (k.kapali_adet if k else None), u.kapali_icerik,
             (k.acik_miktar if k else None), u.acik_carpan,
             (k.aciklama if k else ""))
        r += 1
    for k in ekler:
        _yaz(r, k.kategori or "EK ÜRÜNLER", k.urun_ad,
             k.kapali_adet, k.kapali_icerik, k.acik_miktar, k.acik_carpan, k.aciklama)
        r += 1

    widths = [20, 42, 9, 12, 9, 12, 12, 28]
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + j)].width = w
    ws.freeze_panes = "A5"

    from django.http import HttpResponse
    resp = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    fn = f"stok_{sube.ad}_{ay_str}.xlsx".replace(' ', '_')
    resp["Content-Disposition"] = f'attachment; filename="{fn}"'
    wb.save(resp)
    return resp


# =========================================================================
# SEVKİYAT ( /sevkiyat/ ) — katalog tabanlı sipariş sistemi
# =========================================================================
def _katalog_gruplu():
    """Aktif ürünleri form -> kategori olarak gruplar."""
    form_map = {}
    for u in Urun.objects.filter(aktif=True).order_by('form', 'sira', 'ad'):
        form_map.setdefault(u.form, {}).setdefault(u.kategori, []).append(u)
    sonuc = []
    for form_kod, etiket in SevkiyatForm.choices:
        if form_kod in form_map:
            kats = [{'ad': k, 'urunler': v} for k, v in form_map[form_kod].items()]
            sonuc.append({'kod': form_kod, 'etiket': etiket, 'kategoriler': kats})
    return sonuc


def _birim_secenek(urun):
    secs = [urun.birim]
    if urun.ust_birim and urun.ust_birim != urun.birim:
        secs.append(urun.ust_birim)
    return secs


# Sevkiyat kataloğunu düzenleyebilen roller (değişiklik tüm şeflere anında yansır)
SEVKIYAT_DUZENLE_ROLLERI = [Rol.SATIN_ALMA, Rol.OPERATOR, Rol.GENEL_MUDUR, Rol.YATIRIMCI]


def sevkiyat_duzenle(request):
    """Operatör/Satın Alma (ve tam yetkililer) sevkiyat kataloğunu düzenler:
    grup seçip ürün ekler/çıkarır, koli içeriği + birimini değiştirir. Şeflere anında yansır."""
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    if _cikis_mi(request):
        return _logout(request)
    personel = _aktif_personel(request)
    if personel is None or personel.rol not in SEVKIYAT_DUZENLE_ROLLERI:
        return redirect('ana_sayfa')

    birimler = [b for b, _ in SevkiyatBirim.choices]
    formlar = [(f, e) for f, e in SevkiyatForm.choices]

    if request.method == 'POST':
        islem = request.POST.get('islem')
        geri_grup = (request.POST.get('geri_grup') or '').strip()
        geri = f"{reverse('sevkiyat_duzenle')}?grup={geri_grup}" if geri_grup else reverse('sevkiyat_duzenle')

        if islem == 'urun_guncelle':
            u = Urun.objects.filter(id=request.POST.get('urun_id')).first()
            if u:
                ad = (request.POST.get('ad') or '').strip()
                try:
                    koli = max(1, int(float((request.POST.get('koli_icerigi') or '1').replace(',', '.'))))
                except Exception:
                    koli = u.koli_icerigi
                birim = request.POST.get('birim')
                if birim not in birimler:
                    birim = u.birim
                ust = (request.POST.get('ust_birim') or '').strip()
                if ust and ust not in birimler:
                    ust = u.ust_birim
                if ad:
                    u.ad = ad[:160]
                u.koli_icerigi = koli
                u.birim = birim
                u.ust_birim = ust
                u.save(update_fields=['ad', 'koli_icerigi', 'birim', 'ust_birim'])
                messages.success(request, f"{u.ad} güncellendi.")
            return redirect(geri)

        if islem == 'urun_cikar':
            u = Urun.objects.filter(id=request.POST.get('urun_id')).first()
            if u:
                u.aktif = False
                u.save(update_fields=['aktif'])
                messages.success(request, f"{u.ad} listeden çıkarıldı.")
            return redirect(geri)

        if islem == 'urun_ekle':
            ad = (request.POST.get('ad') or '').strip()
            kategori = (request.POST.get('kategori') or '').strip() or geri_grup
            form = request.POST.get('form')
            if form not in [f for f, _ in SevkiyatForm.choices]:
                form = SevkiyatForm.HAMMADDE
            try:
                koli = max(1, int(float((request.POST.get('koli_icerigi') or '1').replace(',', '.'))))
            except Exception:
                koli = 1
            birim = request.POST.get('birim')
            if birim not in birimler:
                birim = SevkiyatBirim.ADET
            ust = (request.POST.get('ust_birim') or '').strip()
            if ust and ust not in birimler:
                ust = ''
            if ad and kategori:
                var = Urun.objects.filter(form=form, ad=ad).first()
                if var:
                    var.kategori = kategori
                    var.koli_icerigi = koli
                    var.birim = birim
                    var.ust_birim = ust
                    var.aktif = True
                    var.save()
                    messages.success(request, f"{ad} güncellendi (zaten vardı, yeniden eklendi).")
                else:
                    son = Urun.objects.filter(form=form).order_by('-sira').first()
                    Urun.objects.create(form=form, kategori=kategori, ad=ad[:160],
                                        koli_icerigi=koli, birim=birim, ust_birim=ust,
                                        sira=(son.sira + 1 if son else 0), aktif=True)
                    messages.success(request, f"{ad} eklendi.")
                geri = f"{reverse('sevkiyat_duzenle')}?grup={kategori}"
            else:
                messages.error(request, "Ürün adı ve grup zorunlu.")
            return redirect(geri)

        return redirect(geri)

    # GET — grup listesi + seçili grubun ürünleri
    aktif_urunler = list(Urun.objects.filter(aktif=True).order_by('form', 'sira', 'ad'))
    grup_sira = []
    grup_form = {}
    for u in aktif_urunler:
        if u.kategori not in grup_form:
            grup_form[u.kategori] = u.form
            grup_sira.append(u.kategori)
    sel_grup = request.GET.get('grup') or (grup_sira[0] if grup_sira else '')
    urunler = [u for u in aktif_urunler if u.kategori == sel_grup]
    sel_form = grup_form.get(sel_grup, SevkiyatForm.HAMMADDE)

    return render(request, 'sevkiyat_duzenle.html', {
        'personel': personel, 'aktif': 'sevkiyat_duzenle',
        'gruplar': grup_sira, 'sel_grup': sel_grup, 'sel_form': sel_form,
        'urunler': urunler, 'birimler': birimler, 'formlar': formlar,
    })


import calendar as _calmod
_AY_ADLARI = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
              'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
_GUN_KISA = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']


def _takvim_kur(yil, ay, sel_gun, sayac):
    """Ay grid'i: haftalar -> günler. sayac: {date: adet}."""
    cal = _calmod.Calendar(firstweekday=0)
    bugun = timezone.localdate()
    haftalar = []
    for week in cal.monthdatescalendar(yil, ay):
        satir = []
        for d in week:
            satir.append({
                'no': d.day, 'gun': d.isoformat(), 'bu_ay': (d.month == ay),
                'sayi': sayac.get(d, 0), 'secili': (sel_gun == d), 'bugun': (d == bugun),
            })
        haftalar.append(satir)
    onceki = datetime.date(yil, ay, 1) - datetime.timedelta(days=1)
    sonraki = (datetime.date(yil, ay, 28) + datetime.timedelta(days=10)).replace(day=1)
    return {
        'yil': yil, 'ay': ay, 'ay_adi': _AY_ADLARI[ay], 'gun_basliklari': _GUN_KISA,
        'haftalar': haftalar,
        'prev': '%04d-%02d' % (onceki.year, onceki.month),
        'next': '%04d-%02d' % (sonraki.year, sonraki.month),
    }


def _gecmis_hazirla(request, sel_id, izin_ids=None):
    """Seçili ay/gün + şubeye göre takvim verisi ve sipariş listesi döndürür.
    izin_ids verilirse (bölge müdürü) yalnızca o şubeler kapsanır."""
    bugun = timezone.localdate()
    yil, ay = bugun.year, bugun.month
    sel_gun = None
    gun_str = request.GET.get('gun')
    if gun_str:
        try:
            sel_gun = datetime.date.fromisoformat(gun_str)
            yil, ay = sel_gun.year, sel_gun.month
        except ValueError:
            sel_gun = None
    if sel_gun is None:
        ay_str = request.GET.get('ay')
        if ay_str:
            try:
                yil, ay = (int(x) for x in ay_str.split('-'))
            except (ValueError, TypeError):
                yil, ay = bugun.year, bugun.month
    ay_basi = datetime.date(yil, ay, 1)
    son_gun = _calmod.monthrange(yil, ay)[1]
    ay_sonu = datetime.date(yil, ay, son_gun)

    qs = SevkiyatTalep.objects.filter(olusturma__date__gte=ay_basi, olusturma__date__lte=ay_sonu)
    if izin_ids is not None:
        qs = qs.filter(sube_id__in=izin_ids)
    if sel_id:
        qs = qs.filter(sube_id=sel_id)
    ay_listesi = list(qs.select_related('sube').prefetch_related('kalemler').order_by('-olusturma')[:500])

    sayac = {}
    for t in ay_listesi:
        g = timezone.localtime(t.olusturma).date()
        sayac[g] = sayac.get(g, 0) + 1

    if sel_gun:
        liste = [t for t in ay_listesi if timezone.localtime(t.olusturma).date() == sel_gun]
    else:
        liste = ay_listesi
    return _takvim_kur(yil, ay, sel_gun, sayac), liste, sel_gun


def sevkiyat_sayfa(request):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    if _cikis_mi(request):
        return _logout(request)
    personel = _aktif_personel(request)
    if personel is None:
        return redirect('ana_sayfa')
    rol = personel.rol
    is_sef = rol == Rol.SEF
    is_satinalma = rol == Rol.SATIN_ALMA
    is_sevkiyat = rol == Rol.SEVKIYAT
    is_yon = rol in UST_YONETIM
    cikis_yetkili = (rol in (Rol.GENEL_MUDUR, Rol.YATIRIMCI)) or is_satinalma
    if not (is_sef or is_satinalma or is_sevkiyat or is_yon):
        return redirect('ana_sayfa')

    if request.method == 'POST' and is_sef and request.POST.get('islem') == 'siparis_olustur':
        if not personel.sube:
            messages.error(request, "Şubeniz tanımlı değil. Yöneticinize başvurun.")
            return redirect('sevkiyat')
        not_metni = request.POST.get('not_metni', '').strip()[:400]
        secilen = []
        for u in Urun.objects.filter(aktif=True):
            raw = request.POST.get('miktar_%s' % u.id, '').strip().replace(',', '.')
            if not raw:
                continue
            try:
                miktar = Decimal(raw)
            except Exception:
                continue
            if miktar <= 0:
                continue
            birim = request.POST.get('birim_%s' % u.id, u.birim)
            if birim not in _birim_secenek(u):
                birim = u.birim
            secilen.append((u, miktar, birim))
        # Listede olmayan (özel) ürünler
        ek_urunler = request.POST.getlist('ek_urun')
        ek_miktarlar = request.POST.getlist('ek_miktar')
        ek_birimler = request.POST.getlist('ek_birim')
        gecerli_birimler = [b for b, _ in SevkiyatBirim.choices]
        ekstra = []
        for ad, mik, bir in zip(ek_urunler, ek_miktarlar, ek_birimler):
            ad = ad.strip()[:160]
            if not ad:
                continue
            try:
                miktar = Decimal((mik or '').strip().replace(',', '.'))
            except Exception:
                continue
            if miktar <= 0:
                continue
            bir = bir if bir in gecerli_birimler else SevkiyatBirim.ADET
            ekstra.append((ad, miktar, bir))
        if secilen or ekstra:
            talep = SevkiyatTalep.objects.create(
                sube=personel.sube, olusturan=personel,
                olusturan_ad=personel.ad_soyad, not_metni=not_metni)
            for u, miktar, birim in secilen:
                SevkiyatKalem.objects.create(
                    talep=talep, urun=u, urun_ad=u.ad, kategori=u.kategori, form=u.form,
                    koli_icerigi=u.koli_icerigi, istenen_miktar=miktar, istenen_birim=birim)
            for ad, miktar, bir in ekstra:
                SevkiyatKalem.objects.create(
                    talep=talep, urun=None, urun_ad=ad, kategori='DİĞER', form='',
                    koli_icerigi=1, istenen_miktar=miktar, istenen_birim=bir)
            SiparisHareket.objects.create(talep=talep, mesaj="Sipariş oluşturuldu",
                                          yapan_ad=personel.ad_soyad)
            messages.success(request, "Sipariş oluşturuldu (#%s, %s kalem)." % (
                talep.id, len(secilen) + len(ekstra)))
        else:
            messages.error(request, "En az bir ürüne miktar girin.")
        return redirect('sevkiyat')

    if request.method == 'POST' and is_satinalma and request.POST.get('islem') == 'satinalma_tamamla':
        talep = (SevkiyatTalep.objects.filter(id=request.POST.get('talep_id'), durum=SevkiyatDurumu.TALEP)
                 .prefetch_related('kalemler').first())
        if talep:
            gecerli = [b for b, _ in SevkiyatBirim.choices]
            for k in talep.kalemler.all():
                raw = request.POST.get('sa_miktar_%s' % k.id, '').strip().replace(',', '.')
                try:
                    miktar = Decimal(raw)
                except Exception:
                    miktar = k.istenen_miktar
                if miktar < 0:
                    miktar = Decimal(0)
                birim = request.POST.get('sa_birim_%s' % k.id, k.istenen_birim)
                if birim not in gecerli:
                    birim = k.istenen_birim
                k.satinalma_miktar = miktar
                k.satinalma_birim = birim
                k.save()
            talep.durum = SevkiyatDurumu.SEVKIYATTA
            talep.satin_alan_ad = personel.ad_soyad
            talep.satin_alma_tarih = timezone.now()
            talep.save()
            SiparisHareket.objects.create(talep=talep, mesaj="Satın alma tamamlandı, depoya iletildi",
                                          yapan_ad=personel.ad_soyad)
            messages.success(request, "#%s sevkiyata iletildi." % talep.id)
        return redirect('sevkiyat')

    if request.method == 'POST' and is_sevkiyat and request.POST.get('islem') == 'sevkiyat_onayla':
        talep = (SevkiyatTalep.objects.filter(id=request.POST.get('talep_id'),
                 durum__in=[SevkiyatDurumu.SEVKIYATTA, SevkiyatDurumu.REDDEDILDI])
                 .prefetch_related('kalemler').first())
        if talep:
            gecerli = [b for b, _ in SevkiyatBirim.choices]
            for k in talep.kalemler.all():
                varsayilan = k.satinalma_miktar if k.satinalma_miktar is not None else k.istenen_miktar
                raw = request.POST.get('sv_miktar_%s' % k.id, '').strip().replace(',', '.')
                try:
                    miktar = Decimal(raw)
                except Exception:
                    miktar = varsayilan
                if miktar < 0:
                    miktar = Decimal(0)
                birim = request.POST.get('sv_birim_%s' % k.id) or (k.satinalma_birim or k.istenen_birim)
                if birim not in gecerli:
                    birim = k.satinalma_birim or k.istenen_birim
                k.sevkiyat_miktar = miktar
                k.sevkiyat_birim = birim
                k.save()
            talep.durum = SevkiyatDurumu.ONAY_BEKLIYOR
            talep.sevkiyatci_ad = personel.ad_soyad
            talep.sevkiyat_tarih = timezone.now()
            talep.red_notu = ''
            talep.save()
            SiparisHareket.objects.create(talep=talep, mesaj="Sevkiyat hazırlandı, çıkış onayına gönderildi",
                                          yapan_ad=personel.ad_soyad)
            messages.success(request, "#%s çıkış onayına gönderildi." % talep.id)
        return redirect('sevkiyat')

    if request.method == 'POST' and cikis_yetkili and request.POST.get('islem') == 'cikis_onayla':
        talep = SevkiyatTalep.objects.filter(id=request.POST.get('talep_id'),
                                             durum=SevkiyatDurumu.ONAY_BEKLIYOR).first()
        if talep:
            talep.durum = SevkiyatDurumu.ONAYLANDI
            talep.onaylayan_ad = personel.ad_soyad
            talep.onay_tarih = timezone.now()
            talep.save()
            SiparisHareket.objects.create(talep=talep, mesaj="Çıkış onaylandı", yapan_ad=personel.ad_soyad)
            messages.success(request, "#%s onaylandı." % talep.id)
        return redirect('sevkiyat')

    if request.method == 'POST' and cikis_yetkili and request.POST.get('islem') == 'cikis_reddet':
        talep = SevkiyatTalep.objects.filter(id=request.POST.get('talep_id'),
                                             durum=SevkiyatDurumu.ONAY_BEKLIYOR).first()
        if talep:
            aciklama = request.POST.get('red_notu', '').strip()[:400]
            talep.durum = SevkiyatDurumu.REDDEDILDI
            talep.red_notu = aciklama
            talep.save()
            SiparisHareket.objects.create(talep=talep, mesaj="Çıkış reddedildi", aciklama=aciklama,
                                          yapan_ad=personel.ad_soyad)
            messages.success(request, "#%s reddedildi, sevkiyata geri gönderildi." % talep.id)
        return redirect('sevkiyat')

    ctx = {
        'personel': personel, 'aktif': 'sevkiyat',
        'is_sef': is_sef, 'is_satinalma': is_satinalma, 'is_sevkiyat': is_sevkiyat, 'is_yon': is_yon,
        'belge_yetkili': (not is_sef) and rol != Rol.MUDUR,
    }

    ctx['cikis_yetkili'] = cikis_yetkili
    ctx['tum_birimler'] = [b for b, _ in SevkiyatBirim.choices]

    if is_sef:
        katalog = _katalog_gruplu()
        for f in katalog:
            for kat in f['kategoriler']:
                kat['urunler'] = [{'u': u, 'birimler': _birim_secenek(u)} for u in kat['urunler']]
        ctx['katalog'] = katalog
        ctx['ek_oneri'] = list(SevkiyatKalem.objects.filter(urun__isnull=True)
                               .values_list('urun_ad', flat=True).distinct().order_by('urun_ad')[:200])
        sefler = list(SevkiyatTalep.objects.filter(sube=personel.sube)
                      .prefetch_related('kalemler', 'hareketler')[:50])
        for t in sefler:
            t.mode = 'read'
        ctx['talepler'] = sefler
    elif is_satinalma:
        subeler = _yon_subeler(personel)
        sel_id = request.GET.get('sube')
        try:
            sel_id = int(sel_id) if sel_id else None
        except (TypeError, ValueError):
            sel_id = None
        bekleyen = SevkiyatTalep.objects.filter(durum=SevkiyatDurumu.TALEP)
        if sel_id:
            bekleyen = bekleyen.filter(sube_id=sel_id)
        bekleyen = list(bekleyen.select_related('sube').prefetch_related('kalemler')[:100])
        for t in bekleyen:
            t.mode = 'sa'
        onaylar = list(SevkiyatTalep.objects.filter(durum=SevkiyatDurumu.ONAY_BEKLIYOR)
                       .select_related('sube').prefetch_related('kalemler')[:100])
        for t in onaylar:
            t.mode = 'cikis'
        ctx['talepler'] = onaylar + bekleyen
        takvim, gecmis, sel_gun = _gecmis_hazirla(request, sel_id)
        for t in gecmis:
            t.mode = 'read'
        ctx['subeler'] = subeler
        ctx['sel_id'] = sel_id
        ctx['takvim'] = takvim
        ctx['gecmis_talepler'] = gecmis
        ctx['sel_gun'] = sel_gun
        ctx['gecmis'] = True
    elif is_sevkiyat:
        svt = list(SevkiyatTalep.objects.filter(durum__in=[SevkiyatDurumu.SEVKIYATTA, SevkiyatDurumu.REDDEDILDI])
                   .select_related('sube').prefetch_related('kalemler')[:100])
        for t in svt:
            t.mode = 'sv'
            for k in t.kalemler.all():
                k.sv_def_miktar = (k.sevkiyat_miktar if k.sevkiyat_miktar is not None
                                   else (k.satinalma_miktar if k.satinalma_miktar is not None else k.istenen_miktar))
                k.sv_def_birim = k.sevkiyat_birim or k.satinalma_birim or k.istenen_birim
        ctx['talepler'] = svt
    else:
        subeler = _yon_subeler(personel)
        izin_ids = [s.id for s in subeler] if personel.rol == Rol.MUDUR else None
        sel_id = request.GET.get('sube')
        try:
            sel_id = int(sel_id) if sel_id else None
        except (TypeError, ValueError):
            sel_id = None
        if izin_ids is not None and sel_id not in izin_ids:
            sel_id = None
        aktif = []
        if cikis_yetkili:
            aq = SevkiyatTalep.objects.filter(durum=SevkiyatDurumu.ONAY_BEKLIYOR)
            if sel_id:
                aq = aq.filter(sube_id=sel_id)
            aktif = list(aq.select_related('sube').prefetch_related('kalemler')[:100])
            for t in aktif:
                t.mode = 'cikis'
        ctx['talepler'] = aktif
        takvim, gecmis, sel_gun = _gecmis_hazirla(request, sel_id, izin_ids=izin_ids)
        for t in gecmis:
            t.mode = 'read'
        ctx['subeler'] = subeler
        ctx['sel_id'] = sel_id
        ctx['takvim'] = takvim
        ctx['gecmis_talepler'] = gecmis
        ctx['sel_gun'] = sel_gun
        ctx['gecmis'] = True

    return render(request, 'sevkiyat.html', ctx)


# =========================================================================
# SEVKİYAT BELGE İNDİRME (PDF) — yükleme belgesi & teslim fişi
# =========================================================================
def sevkiyat_belge(request, talep_id, tip):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    personel = _aktif_personel(request)
    if personel is None:
        return redirect('ana_sayfa')
    if personel.rol in (Rol.SEF, Rol.MUDUR):
        return redirect('sevkiyat')
    if tip not in ('yukleme', 'fis'):
        return redirect('sevkiyat')
    talep = (SevkiyatTalep.objects.filter(id=talep_id)
             .select_related('sube').prefetch_related('kalemler').first())
    if talep is None:
        return redirect('sevkiyat')
    rol = personel.rol
    yetkili = rol in OFIS_ROLLERI or (rol == Rol.SEF and personel.sube_id == talep.sube_id)
    if not yetkili:
        return redirect('ana_sayfa')
    if tip == 'yukleme' and talep.durum not in (SevkiyatDurumu.SEVKIYATTA,
                                                SevkiyatDurumu.ONAY_BEKLIYOR, SevkiyatDurumu.ONAYLANDI):
        return redirect('sevkiyat')
    if tip == 'fis' and talep.durum != SevkiyatDurumu.ONAYLANDI:
        return redirect('sevkiyat')
    from .sevkiyat_pdf import sevkiyat_pdf_bytes
    pdf = sevkiyat_pdf_bytes(talep, tip)
    adi = 'yukleme_belgesi' if tip == 'yukleme' else 'teslim_fisi'
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = 'inline; filename="sevkiyat_%s_%s.pdf"' % (talep.id, adi)
    return resp


def sevkiyat_excel(request, talep_id):
    """Onaylanan siparişi orijinal talep formu şablonuna doldurup indirir."""
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    personel = _aktif_personel(request)
    if personel is None:
        return redirect('ana_sayfa')
    if personel.rol in (Rol.SEF, Rol.MUDUR):
        return redirect('sevkiyat')
    talep = (SevkiyatTalep.objects.filter(id=talep_id, durum=SevkiyatDurumu.ONAYLANDI)
             .select_related('sube').prefetch_related('kalemler').first())
    if talep is None:
        return redirect('sevkiyat')
    if personel.rol not in OFIS_ROLLERI:
        return redirect('ana_sayfa')
    from .sevkiyat_excel import siparis_excel_bytes
    data = siparis_excel_bytes(talep)
    resp = HttpResponse(data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = 'attachment; filename="siparis_%s_%s.xlsx"' % (
        talep.id, talep.olusturma.strftime('%Y%m%d'))
    return resp


# =========================================================================
# GİRİŞ YARDIMCILARI
# =========================================================================
def _kod_giris(request):
    ip = _istemci_ip(request)
    kilit, _ = KodKilit.objects.get_or_create(ip=ip)
    now = timezone.now()
    if kilit.kilit_bitis and now < kilit.kilit_bitis:
        kalan = int((kilit.kilit_bitis - now).total_seconds() // 60) + 1
        messages.error(request, f"Çok fazla hatalı deneme. Lütfen {kalan} dakika sonra tekrar deneyin.")
        return redirect('ana_sayfa')
    kod = request.POST.get('kod', '').strip()
    personel = Personel.objects.filter(giris_kodu=kod, rol__in=[Rol.PERSONEL, Rol.SEF]).select_related('user').first()
    if personel and personel.user:
        kilit.hatali_deneme = 0
        kilit.kilit_bitis = None
        kilit.save()
        personel.user.backend = MODEL_BACKEND
        auth_login(request, personel.user)
        return redirect('ana_sayfa')
    kilit.hatali_deneme += 1
    if kilit.hatali_deneme >= MAX_DENEME:
        kilit.kilit_bitis = now + datetime.timedelta(minutes=KILIT_DK)
        kilit.hatali_deneme = 0
        messages.error(request, f"Çok fazla hatalı deneme. {KILIT_DK} dakika boyunca giriş kapatıldı.")
    else:
        messages.error(request, f"Kod hatalı. Kalan deneme hakkı: {MAX_DENEME - kilit.hatali_deneme}.")
    kilit.save()
    return redirect('ana_sayfa')


def _sifre_giris(request):
    user = authenticate(request, username=request.POST.get('kullanici_adi', '').strip(),
                        password=request.POST.get('sifre', ''))
    if user is not None:
        auth_login(request, user)
        return redirect('ana_sayfa')
    messages.error(request, 'Kullanıcı adı veya şifre hatalı.')
    return redirect('/?mod=yonetici')


def _hukuki(request, anahtar):
    return render(request, 'hukuki.html', HUKUKI_SAYFALAR[anahtar])

def kvkk(request):
    return _hukuki(request, 'kvkk')

def kullanim_kosullari(request):
    return _hukuki(request, 'kullanim_kosullari')

def gizlilik(request):
    return _hukuki(request, 'gizlilik')


# ---------------------------------------------------------------------------
# PWA: manifest + service worker (uygulama olarak yüklenebilirlik)
# ---------------------------------------------------------------------------
_PWA_MANIFEST = {
    "name": "Geek Coffee & Eatery Panel",
    "short_name": "Geek Panel",
    "description": "Geek Coffee & Eatery personel ve sevkiyat yönetim paneli",
    "lang": "tr",
    "dir": "ltr",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "orientation": "portrait-primary",
    "background_color": "#ffffff",
    "theme_color": "#162AA3",
    "icons": [
        {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "/icons/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}

_PWA_SW = """
const STATIK = 'geek-statik-v2';
const KABUK = 'geek-kabuk-v2';
const KABUK_URL = '/';
self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(KABUK).then(function (c) { return c.add(KABUK_URL); }).catch(function () {})
  );
  self.skipWaiting();
});
self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (ks) {
      return Promise.all(ks.filter(function (k) { return k !== STATIK && k !== KABUK; })
                           .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});
self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== location.origin) return;
  // Statik dosyalar: önce önbellek (hızlı + çevrimdışı çalışır).
  if (url.pathname.indexOf('/static/') === 0) {
    e.respondWith(
      caches.open(STATIK).then(function (c) {
        return c.match(req).then(function (hit) {
          return hit || fetch(req).then(function (res) {
            if (res && res.status === 200) c.put(req, res.clone());
            return res;
          });
        });
      })
    );
    return;
  }
  // Sayfa gezinmeleri: önce ağ (her zaman güncel), çevrimdışıysa kabuk.
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req).catch(function () { return caches.match(KABUK_URL); })
    );
    return;
  }
});
"""


def pwa_manifest(request):
    return HttpResponse(json.dumps(_PWA_MANIFEST, ensure_ascii=False),
                        content_type='application/manifest+json')


_PWA_IKON_IZIN = {'icon-192.png', 'icon-512.png', 'icon-512-maskable.png', 'icon-180.png'}


def pwa_icon(request, ad):
    """İkonları doğrudan Django üzerinden sunar (statik eşlemeden bağımsız)."""
    import os
    from django.conf import settings
    from django.http import Http404
    if ad not in _PWA_IKON_IZIN:
        raise Http404("ikon yok")
    yol = os.path.join(settings.BASE_DIR, 'static', 'icons', ad)
    try:
        with open(yol, 'rb') as f:
            data = f.read()
    except OSError:
        raise Http404("ikon dosyası bulunamadı")
    resp = HttpResponse(data, content_type='image/png')
    resp['Cache-Control'] = 'public, max-age=604800'
    return resp


def pwa_service_worker(request):
    resp = HttpResponse(_PWA_SW, content_type='application/javascript')
    resp['Service-Worker-Allowed'] = '/'
    resp['Cache-Control'] = 'no-cache'
    return resp


# =========================================================================
# GÜNLÜK KAHVE SORUSU (personel + şef)
# =========================================================================
SORU_ROLLERI = [Rol.PERSONEL, Rol.SEF]
SORU_SURE = 30           # saniye (kullanıcıya gösterilen sayaç)
SORU_SURE_PAYLI = 38     # sunucu tarafı tolerans (ağ gecikmesi)
CALISMAYAN_TIPLER = [VardiyaTipi.IZINLI, VardiyaTipi.RAPORLU, VardiyaTipi.DEVAMSIZ]
# Bilgi karnesini görebilen roller (şube bazlı)
KARNE_ROLLERI = [Rol.EGITMEN, Rol.MUDUR, Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI]
# Soru bankasını yönetebilen roller (ekle/çıkar/aktif-pasif)
SORU_YONETIM_ROLLERI = [Rol.EGITMEN, Rol.GENEL_MUDUR]


def _soru_sistemi_aktif():
    return SoruAyar.get().aktif


def _egitmen_mi(personel):
    """Kişi eğitmen yetkisine sahip mi (işaret veya eski Eğitmen rolü)."""
    return bool(personel) and (getattr(personel, 'egitmen', False) or personel.rol == Rol.EGITMEN)


def _karne_gorebilir(personel):
    return bool(personel) and (_egitmen_mi(personel) or personel.rol in
                               [Rol.MUDUR, Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI])


def _soru_yonetebilir(personel):
    return bool(personel) and (_egitmen_mi(personel) or personel.rol == Rol.GENEL_MUDUR)


def _bugun_calisiyor_mu(personel, gun):
    """O gün izinli/raporlu/devamsız ise False; aksi halde (kayıt yoksa da) True."""
    v = personel.vardiyalar.filter(tarih=gun).first()
    if v and v.vardiya_tipi in CALISMAYAN_TIPLER:
        return False
    return True


def _gunluk_soru_getir_veya_ata(personel, gun):
    """O güne ait GunlukSoru'yu döndürür; yoksa (ve çalışma günüyse) yeni atar.
    Çalışma günü değilse None döner."""
    gs = GunlukSoru.objects.filter(personel=personel, tarih=gun).first()
    if gs:
        return gs
    if not _bugun_calisiyor_mu(personel, gun):
        return None
    aktif_ids = list(KahveSoru.objects.filter(aktif=True).values_list('id', flat=True))
    if not aktif_ids:
        return None
    gorulen = set(GunlukSoru.objects.filter(personel=personel)
                  .values_list('soru_id', flat=True))
    havuz = [i for i in aktif_ids if i not in gorulen] or aktif_ids
    soru_id = random.choice(havuz)
    sube = personel.sube
    return GunlukSoru.objects.create(
        personel=personel, sube=sube, sube_ad=(sube.ad if sube else ''),
        soru_id=soru_id, tarih=gun)


def _gunluk_finalize(gs):
    """Süresi dolmuş ama cevaplanmamış soruyu yanlış olarak kapatır."""
    if gs and gs.baslangic and not gs.cevaplandi:
        gecen = (timezone.now() - gs.baslangic).total_seconds()
        if gecen > SORU_SURE_PAYLI:
            gs.cevaplandi = True
            gs.sure_doldu = True
            gs.dogru_mu = False
            gs.secilen = ''
            gs.save(update_fields=['cevaplandi', 'sure_doldu', 'dogru_mu', 'secilen'])


def gunluk_soru(request):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    if _cikis_mi(request):
        return _logout(request)
    personel = _aktif_personel(request)
    if personel is None or personel.rol not in SORU_ROLLERI:
        return redirect('ana_sayfa')
    if not _soru_sistemi_aktif():
        return redirect('ana_sayfa')

    today = timezone.localdate()
    gs = _gunluk_soru_getir_veya_ata(personel, today)
    if gs is None:
        return redirect('ana_sayfa')
    _gunluk_finalize(gs)
    if gs.cevaplandi:
        return redirect('ana_sayfa')

    if request.method == 'POST':
        # Sunucu tarafı süre kontrolü
        suresi_doldu = False
        if gs.baslangic:
            gecen = (timezone.now() - gs.baslangic).total_seconds()
            suresi_doldu = gecen > SORU_SURE_PAYLI
        secilen = (request.POST.get('secilen') or '').strip().upper()
        if secilen not in ('A', 'B', 'C', 'D'):
            secilen = ''
        if suresi_doldu or not secilen:
            gs.secilen = '' if suresi_doldu else secilen
            gs.sure_doldu = suresi_doldu
            gs.dogru_mu = False
        else:
            gs.secilen = secilen
            gs.dogru_mu = (gs.soru is not None and secilen == gs.soru.dogru)
        gs.cevaplandi = True
        gs.save()
        if gs.dogru_mu:
            messages.success(request, "Doğru cevap! 🎉")
        elif gs.sure_doldu:
            messages.error(request, "Süre doldu, soru boş işlendi.")
        else:
            dogru_txt = gs.soru.sik(gs.soru.dogru) if gs.soru else ''
            messages.error(request, f"Yanlış. Doğru cevap: {dogru_txt}")
        return redirect('ana_sayfa')

    # GET — sayaç başlangıcını ilk gösterimde sabitle
    if gs.baslangic is None:
        gs.baslangic = timezone.now()
        gs.save(update_fields=['baslangic'])
    gecen = (timezone.now() - gs.baslangic).total_seconds()
    kalan = max(1, int(SORU_SURE - gecen))
    return render(request, 'gunluk_soru.html', {
        'personel': personel, 'aktif': 'home', 'gs': gs, 'soru': gs.soru,
        'kalan': kalan, 'sure': SORU_SURE,
    })


def bilgi_karnesi(request):
    """Yönetim: şube + ay seçip personelin aylık bilgi kapasitesini ve yanlışları görür."""
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    if _cikis_mi(request):
        return _logout(request)
    personel = _aktif_personel(request)
    if personel is None or not _karne_gorebilir(personel):
        return redirect('ana_sayfa')

    subeler = _yon_subeler(personel)
    sel_sube = _yonetici_sube(request, subeler)
    ay_str = request.GET.get('ay') or timezone.localdate().strftime('%Y-%m')
    try:
        ay_ilk, sonraki = _ay_araligi(ay_str)
    except Exception:
        ay_ilk, sonraki = _ay_araligi(timezone.localdate().strftime('%Y-%m'))
        ay_str = ay_ilk.strftime('%Y-%m')

    satirlar = []
    yanlislar = []
    if sel_sube:
        kisiler = (Personel.objects.filter(sube=sel_sube, rol__in=SORU_ROLLERI, aktif=True)
                   .order_by('ad_soyad'))
        kayitlar = (GunlukSoru.objects.filter(personel__in=kisiler,
                                              tarih__gte=ay_ilk, tarih__lt=sonraki)
                    .select_related('soru', 'personel'))
        # süresi geçmiş ama kapanmamışları kapat
        for gs in kayitlar:
            _gunluk_finalize(gs)
        per_map = {k.id: {'personel': k, 'toplam': 0, 'dogru': 0, 'yanlis': 0, 'bos': 0}
                   for k in kisiler}
        for gs in kayitlar:
            d = per_map.get(gs.personel_id)
            if not d:
                continue
            d['toplam'] += 1
            if not gs.cevaplandi:
                # henüz cevaplanmamış (bugünün sorusu olabilir) — sayma
                d['toplam'] -= 1
                continue
            if gs.dogru_mu:
                d['dogru'] += 1
            elif gs.sure_doldu or not gs.secilen:
                d['bos'] += 1
                d['yanlis'] += 1
            else:
                d['yanlis'] += 1
            if gs.cevaplandi and not gs.dogru_mu and gs.soru:
                yanlislar.append({
                    'ad': gs.personel.ad_soyad, 'tarih': gs.tarih, 'soru': gs.soru.metin,
                    'secilen': (gs.soru.sik(gs.secilen) if gs.secilen else '—'),
                    'dogru': gs.soru.sik(gs.soru.dogru),
                    'bos': gs.sure_doldu or not gs.secilen,
                })
        for d in per_map.values():
            t = d['toplam']
            d['basari'] = round(d['dogru'] * 100 / t) if t else 0
            satirlar.append(d)
        satirlar.sort(key=lambda x: (-x['basari'], x['personel'].ad_soyad))
        yanlislar.sort(key=lambda x: x['tarih'], reverse=True)

    return render(request, 'bilgi_karnesi.html', {
        'personel': personel, 'aktif': 'bilgi_karnesi',
        'subeler': subeler, 'sel_sube': sel_sube, 'selected_ay_str': ay_str,
        'satirlar': satirlar, 'yanlislar': yanlislar,
    })


def soru_yonetimi(request):
    """Eğitmen (ve GM): soru bankasını yönetir — ekle/düzenle/aktif-pasif + sistemi aç/kapat."""
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    if _cikis_mi(request):
        return _logout(request)
    personel = _aktif_personel(request)
    if personel is None or not _soru_yonetebilir(personel):
        return redirect('ana_sayfa')

    ayar = SoruAyar.get()

    if request.method == 'POST':
        islem = request.POST.get('islem')

        if islem == 'sistem_durum':
            ayar.aktif = (request.POST.get('aktif') == '1')
            ayar.save(update_fields=['aktif', 'guncelleme'])
            messages.success(request, "Günlük soru sistemi " + ("aktif edildi." if ayar.aktif else "pasife alındı."))
            return redirect('soru_yonetimi')

        if islem == 'soru_ekle':
            metin = (request.POST.get('metin') or '').strip()
            a = (request.POST.get('sik_a') or '').strip()
            b = (request.POST.get('sik_b') or '').strip()
            c = (request.POST.get('sik_c') or '').strip()
            d = (request.POST.get('sik_d') or '').strip()
            dogru = (request.POST.get('dogru') or '').strip().upper()
            kategori = (request.POST.get('kategori') or '').strip()[:40]
            if metin and a and b and c and d and dogru in ('A', 'B', 'C', 'D'):
                KahveSoru.objects.create(metin=metin, sik_a=a[:200], sik_b=b[:200],
                                         sik_c=c[:200], sik_d=d[:200], dogru=dogru,
                                         kategori=kategori, aktif=True)
                messages.success(request, "Soru eklendi.")
            else:
                messages.error(request, "Tüm alanlar ve geçerli bir doğru şık (A/B/C/D) zorunlu.")
            return redirect('soru_yonetimi')

        if islem == 'soru_guncelle':
            s = KahveSoru.objects.filter(id=request.POST.get('soru_id')).first()
            if s:
                metin = (request.POST.get('metin') or '').strip()
                a = (request.POST.get('sik_a') or '').strip()
                b = (request.POST.get('sik_b') or '').strip()
                c = (request.POST.get('sik_c') or '').strip()
                d = (request.POST.get('sik_d') or '').strip()
                dogru = (request.POST.get('dogru') or '').strip().upper()
                if metin and a and b and c and d and dogru in ('A', 'B', 'C', 'D'):
                    s.metin = metin
                    s.sik_a, s.sik_b, s.sik_c, s.sik_d = a[:200], b[:200], c[:200], d[:200]
                    s.dogru = dogru
                    s.kategori = (request.POST.get('kategori') or '').strip()[:40]
                    s.save()
                    messages.success(request, "Soru güncellendi.")
                else:
                    messages.error(request, "Geçersiz soru bilgisi.")
            return redirect('soru_yonetimi')

        if islem == 'soru_durum':
            s = KahveSoru.objects.filter(id=request.POST.get('soru_id')).first()
            if s:
                s.aktif = not s.aktif
                s.save(update_fields=['aktif'])
                messages.success(request, ("Soru aktif edildi." if s.aktif else "Soru pasife alındı (çıkarıldı)."))
            return redirect('soru_yonetimi')

        return redirect('soru_yonetimi')

    # GET
    arama = (request.GET.get('q') or '').strip()
    kategori = (request.GET.get('kategori') or '').strip()
    qs = KahveSoru.objects.all().order_by('-aktif', 'kategori', 'id')
    if arama:
        qs = qs.filter(metin__icontains=arama)
    if kategori:
        qs = qs.filter(kategori=kategori)
    sorular = list(qs)
    kategoriler = sorted(set(KahveSoru.objects.exclude(kategori='')
                             .values_list('kategori', flat=True)))
    return render(request, 'soru_yonetimi.html', {
        'personel': personel, 'aktif': 'soru_yonetimi',
        'ayar': ayar, 'sorular': sorular, 'kategoriler': kategoriler,
        'arama': arama, 'sel_kategori': kategori,
        'toplam': len(sorular),
        'aktif_sayi': KahveSoru.objects.filter(aktif=True).count(),
    })


# =========================================================================
# STOK DÜZENLE (ortak katalog: ürün ekle/çıkar/detay) — şeflere anında yansır
# =========================================================================
STOK_DUZENLE_ROLLERI = [Rol.MUDUR, Rol.SATIN_ALMA, Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI]


def _dec(v, vars):
    try:
        d = Decimal(str(v).replace(',', '.'))
        return d if d > 0 else vars
    except Exception:
        return vars


def stok_duzenle(request):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    if _cikis_mi(request):
        return _logout(request)
    personel = _aktif_personel(request)
    if personel is None or personel.rol not in STOK_DUZENLE_ROLLERI:
        return redirect('ana_sayfa')

    if request.method == 'POST':
        islem = request.POST.get('islem')
        geri_grup = (request.POST.get('geri_grup') or '').strip()
        geri = f"{reverse('stok_duzenle')}?grup={geri_grup}" if geri_grup else reverse('stok_duzenle')

        if islem == 'urun_guncelle':
            u = StokUrun.objects.filter(id=request.POST.get('urun_id')).first()
            if u:
                ad = (request.POST.get('ad') or '').strip()
                if ad:
                    u.ad = ad[:200]
                u.kategori = (request.POST.get('kategori') or u.kategori).strip()[:80]
                u.kapali_icerik = _dec(request.POST.get('kapali_icerik'), u.kapali_icerik)
                u.acik_carpan = _dec(request.POST.get('acik_carpan'), u.acik_carpan)
                u.save(update_fields=['ad', 'kategori', 'kapali_icerik', 'acik_carpan'])
                messages.success(request, f"{u.ad} güncellendi.")
            return redirect(geri)

        if islem == 'urun_cikar':
            u = StokUrun.objects.filter(id=request.POST.get('urun_id')).first()
            if u:
                u.aktif = False
                u.save(update_fields=['aktif'])
                messages.success(request, f"{u.ad} listeden çıkarıldı.")
            return redirect(geri)

        if islem == 'urun_ekle':
            ad = (request.POST.get('ad') or '').strip()
            kategori = (request.POST.get('kategori') or '').strip() or geri_grup
            kapali = _dec(request.POST.get('kapali_icerik'), Decimal('1'))
            acik = _dec(request.POST.get('acik_carpan'), Decimal('1'))
            if ad and kategori:
                var = StokUrun.objects.filter(ad=ad).first()
                if var:
                    var.kategori = kategori[:80]
                    var.kapali_icerik = kapali
                    var.acik_carpan = acik
                    var.aktif = True
                    var.save()
                    messages.success(request, f"{ad} güncellendi (zaten vardı, yeniden eklendi).")
                else:
                    son = StokUrun.objects.order_by('-sira').first()
                    StokUrun.objects.create(kategori=kategori[:80], ad=ad[:200],
                                            kapali_icerik=kapali, acik_carpan=acik,
                                            sira=(son.sira + 1 if son else 0), aktif=True)
                    messages.success(request, f"{ad} eklendi.")
                geri = f"{reverse('stok_duzenle')}?grup={kategori}"
            else:
                messages.error(request, "Ürün adı ve grup zorunlu.")
            return redirect(geri)

        return redirect(geri)

    aktif_urunler = list(StokUrun.objects.filter(aktif=True).order_by('sira', 'ad'))
    gruplar = []
    for u in aktif_urunler:
        if u.kategori not in gruplar:
            gruplar.append(u.kategori)
    sel_grup = request.GET.get('grup') or (gruplar[0] if gruplar else '')
    urunler = [u for u in aktif_urunler if u.kategori == sel_grup]
    return render(request, 'stok_duzenle.html', {
        'personel': personel, 'aktif': 'stok_duzenle',
        'gruplar': gruplar, 'sel_grup': sel_grup, 'urunler': urunler,
    })
