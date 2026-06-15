import datetime
import secrets
import unicodedata
import base64
from decimal import Decimal, InvalidOperation
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum
from django.core.files.base import ContentFile
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User

from .models import (Personel, KodKilit, Vardiya, Mola, Sube, Puantaj, Zayi, Birim, Kalibrasyon,
                     SevkiyatTalep, SevkiyatKalem, SevkiyatBirim, SevkiyatDurumu,
                     SevkiyatForm, Urun, SiparisHareket,
                     Rol, OnayDurumu, VardiyaTipi)
from .constants import GUNLUK_TOPLAM_MOLA_DK, BIRINCI_MOLA_DK, MOLA_LIMIT_UYARI_DK
from .hukuki_icerik import HUKUKI_SAYFALAR

MAX_DENEME = 5
KILIT_DK = 10
MODEL_BACKEND = 'django.contrib.auth.backends.ModelBackend'
GUN_ADLARI = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
UST_YONETIM = [Rol.GENEL_MUDUR, Rol.MUDUR, Rol.OPERATOR]
# Şifreyle giren, şubeye bağlı olmayan ofis/birim rolleri (Ekip'ten açılır)
OFIS_ROLLERI = [Rol.GENEL_MUDUR, Rol.MUDUR, Rol.OPERATOR, Rol.SATIN_ALMA, Rol.SEVKIYAT]
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


def _puantaj_hesapla(personel, ay_ilk, ay_son):
    rec = Puantaj.objects.filter(personel=personel, ay=ay_ilk).first()
    if rec and rec.manuel_duzenlendi:
        return {'calisilan': rec.calisilan_gun, 'eksik': rec.eksik_gun,
                'izinli': rec.izinli_gun, 'raporlu': rec.raporlu_gun, 'manuel': True}
    # Vardiya girildiği anda yansır (reddedilenler hariç)
    s = personel.vardiyalar.filter(tarih__gte=ay_ilk, tarih__lt=ay_son).exclude(durum=OnayDurumu.REDDEDILDI)
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
    subeler = list(Sube.objects.order_by('ad'))
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
    subeler = list(Sube.objects.order_by('ad')) if is_yon else []
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
    liste = []
    for p in personeller:
        d = _puantaj_hesapla(p, ay_ilk, ay_son)
        d['personel'] = p
        d['hakedis'] = d['calisilan'] + d['izinli'] + d['raporlu']
        liste.append(d)
    return render(request, 'puantaj.html', {
        'personel': personel, 'aktif': 'puantaj', 'is_gm': is_gm, 'is_yon': is_yon,
        'subeler': subeler, 'sel_sube': sel_sube, 'puantaj_listesi': liste,
        'selected_ay_str': ay_str,
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
    subeler = list(Sube.objects.order_by('ad')) if is_yon else []
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

    subeler = list(Sube.objects.order_by('ad'))
    if request.method == 'POST':
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

    yoneticiler = list(Personel.objects.filter(rol__in=OFIS_ROLLERI).select_related('user').order_by('ad_soyad'))
    sefler = list(Personel.objects.filter(rol=Rol.SEF).select_related('sube').order_by('ad_soyad'))
    return render(request, 'ekip.html', {
        'personel': personel, 'aktif': 'ekip', 'subeler': subeler,
        'yoneticiler': yoneticiler, 'sefler': sefler,
        'yonetici_rolleri': OFIS_ROLLERI,
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
    if p.rol == Rol.SEF:
        subeler = Sube.objects.filter(id=p.sube_id) if p.sube_id else Sube.objects.none()
    else:
        sid = request.GET.get('sube_id') or request.session.get('sel_sube_id')
        subeler = Sube.objects.filter(id=sid) if sid else Sube.objects.order_by('ad')

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
    ws["A1"] = f"GEEK PANEL — Aylık Puantaj ({ay_str})"
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
            d = _puantaj_hesapla(pp, ay_ilk, ay_son)
            ws.cell(row=r, column=1, value=pp.ad_soyad).alignment = left
            ws.cell(row=r, column=2, value=pp.rol).alignment = center
            ws.cell(row=r, column=3, value=d['calisilan']).alignment = center
            ws.cell(row=r, column=4, value=d['eksik']).alignment = center
            ws.cell(row=r, column=5, value=d['izinli']).alignment = center
            ws.cell(row=r, column=6, value=d['raporlu']).alignment = center
            hc = ws.cell(row=r, column=7, value=f"=C{r}+E{r}+F{r}")
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
    subeler = list(Sube.objects.order_by('ad')) if is_yon else []
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
    if sel_sube:
        kayitlar = list(Zayi.objects.filter(sube=sel_sube, olusturma__date__gte=ay_ilk,
                                            olusturma__date__lt=ay_son).select_related('giren'))
        if personel.rol == Rol.SEF:
            bugun = timezone.localdate()
            for z in kayitlar:
                z.duzenlenebilir = timezone.localtime(z.olusturma).date() == bugun
        if is_yon:
            agg = list(Zayi.objects.filter(sube=sel_sube, olusturma__date__gte=ay_ilk, olusturma__date__lt=ay_son)
                       .values('urun_adi', 'birim').annotate(toplam=Sum('miktar')).order_by('-toplam'))
            maxv = max((float(a['toplam']) for a in agg), default=0)
            grafik = [{'urun': a['urun_adi'], 'birim': a['birim'], 'toplam': a['toplam'],
                       'yuzde': round(float(a['toplam']) / maxv * 100, 1) if maxv else 0} for a in agg]

    return render(request, 'zayi.html', {
        'personel': personel, 'aktif': 'zayi', 'ekleyebilir': ekleyebilir, 'is_yon': is_yon,
        'subeler': subeler, 'sel_sube': sel_sube, 'kayitlar': kayitlar, 'grafik': grafik,
        'selected_ay_str': ay_str, 'birimler': Birim.choices,
    })


def zayi_excel_export(request):
    if not request.user.is_authenticated:
        return redirect('ana_sayfa')
    p = _aktif_personel(request)
    if not p or p.rol not in UST_YONETIM:
        return redirect('ana_sayfa')
    ay_str = request.GET.get('zayi_ay') or timezone.localdate().strftime('%Y-%m')
    ay_ilk, ay_son = _ay_araligi(ay_str)
    sid = request.GET.get('sube_id') or request.session.get('sel_sube_id')
    sube = Sube.objects.filter(id=sid).first()
    qs = Zayi.objects.filter(olusturma__date__gte=ay_ilk, olusturma__date__lt=ay_son).select_related('sube', 'giren')
    if sube:
        qs = qs.filter(sube=sube)
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
    ws["A1"] = f"GEEK PANEL — Zayi Listesi ({ay_str}{' · ' + sube.ad if sube else ' · Tüm şubeler'})"
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
    subeler = list(Sube.objects.order_by('ad')) if is_yon else []
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
    if urun.birim != SevkiyatBirim.KOLI:
        secs.append(SevkiyatBirim.KOLI)
    return secs


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
    cikis_yetkili = (rol == Rol.GENEL_MUDUR) or is_satinalma
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
        subeler = list(Sube.objects.order_by('ad'))
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
        onaylanan = SevkiyatTalep.objects.filter(durum=SevkiyatDurumu.ONAYLANDI)
        if sel_id:
            onaylanan = onaylanan.filter(sube_id=sel_id)
        onaylanan = list(onaylanan.select_related('sube').prefetch_related('kalemler')[:30])
        for t in onaylanan:
            t.mode = 'read'
        ctx['subeler'] = subeler
        ctx['sel_id'] = sel_id
        ctx['talepler'] = onaylar + bekleyen + onaylanan
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
        subeler = list(Sube.objects.order_by('ad'))
        sel_id = request.GET.get('sube')
        try:
            sel_id = int(sel_id) if sel_id else None
        except (TypeError, ValueError):
            sel_id = None
        qs = SevkiyatTalep.objects.all()
        if sel_id:
            qs = qs.filter(sube_id=sel_id)
        allt = list(qs.select_related('sube').prefetch_related('kalemler')[:200])
        for t in allt:
            t.mode = 'cikis' if (cikis_yetkili and t.durum == SevkiyatDurumu.ONAY_BEKLIYOR) else 'read'
        ctx['subeler'] = subeler
        ctx['sel_id'] = sel_id
        ctx['gecmis'] = True
        ctx['talepler'] = allt

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
