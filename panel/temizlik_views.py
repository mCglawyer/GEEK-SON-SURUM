"""Temizlik malzemesi tüketimi: sayım girişi (şef / mağaza müdürü) ve tüketim raporu (yönetim + şube)."""
import datetime
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from . import temizlik as tz
from .models import (Sube, TemizlikAyar, TemizlikDuzeltme, TemizlikFiyat, TemizlikSayim, TemizlikSayimKalem,
                     TemizlikUrun, Urun)
from .views import _aktif_personel, _cikis_mi, _logout


def _personel(request):
    if not request.user.is_authenticated:
        return None, redirect('ana_sayfa')
    if _cikis_mi(request):
        return None, _logout(request)
    personel = _aktif_personel(request)
    if personel is None:
        return None, redirect('ana_sayfa')
    return personel, None


def _hazir(request):
    """(personel, ayar, yanıt). Sistem kapalıysa yalnızca yönetim girer; diğerleri 'kapalı' sayfası görür."""
    personel, git = _personel(request)
    if git:
        return None, None, git
    if personel.rol not in tz.RAPOR_ROLLERI:
        return None, None, redirect('ana_sayfa')
    ayar = TemizlikAyar.al()
    if not tz.erisebilir(personel, ayar):
        return None, None, render(request, 'temizlik_kapali.html', {'personel': personel, 'aktif': 'temizlik',
                                                                      'ayar': ayar})
    return personel, ayar, None


def _ortak(personel, ayar, sayfa=''):
    """Tüm temizlik sayfalarına: yönetim şeridi (Rapor · Ürünler · Fiyatlar · Ayarlar) ve sistem durumu."""
    menu = []
    if tz.fiyat_gorur(personel):
        if personel.rol in tz.GIRIS_ROLLERI and tz.giris_subeleri(personel):
            menu.append(('Sayım', reverse('temizlik_giris'), 'giris'))
        menu.append(('Rapor', reverse('temizlik_rapor'), 'rapor'))
        if personel.rol in tz.URUN_ROLLERI:
            menu.append(('Ürünler', reverse('temizlik_urunler'), 'urunler'))
        menu.append(('Fiyatlar', reverse('temizlik_fiyatlar'), 'fiyatlar'))
        if personel.rol in tz.AYAR_ROLLERI:
            menu.append(('Ayarlar', reverse('temizlik_ayarlar'), 'ayarlar'))
    return {'tz_menu': [(a, u, k == sayfa) for a, u, k in menu], 'ayar': ayar,
            'sistem_kapali': not ayar.aktif, 'ayar_gorur': personel.rol in tz.AYAR_ROLLERI}


def temizlik_ana(request):
    """Menüdeki tek bağlantı: girebilen rol sayım sayfasına, diğerleri rapora gider."""
    personel, ayar, git = _hazir(request)
    if git:
        return git
    if personel.rol in tz.GIRIS_ROLLERI and tz.giris_subeleri(personel):
        return redirect('temizlik_giris')
    if personel.rol in tz.RAPOR_ROLLERI:
        return redirect('temizlik_rapor')
    return redirect('ana_sayfa')


def _ay_url(ad, ay_ilk, sube):
    q = {'ay': (ad or ay_ilk).strftime('%Y-%m')}
    if sube:
        q['sube'] = sube.id
    return '%s?%s' % (reverse('temizlik_giris'), urlencode(q))


def _tarih_oku(metin):
    try:
        return datetime.datetime.strptime((metin or '').strip(), '%Y-%m-%d').date()
    except ValueError:
        return None


def _ay(request, ayar):
    """İstekteki ay; yoksa varsayılan (bu ay ya da sistem başlangıç ayı)."""
    ham = request.POST.get('ay') or request.GET.get('ay')
    return tz.ay_oku(ham) if ham else tz.varsayilan_ay(ayar)


def _sayim_oku(request, ay_ilk, tur, urunler):
    """Sayım formunu okur. (hata_listesi, degerler{urun: (koli, adet, acik)}, tarih)"""
    etiket = 'İlk stok' if tur == 'ILK' else 'Son stok'
    hatalar = []
    tarih = _tarih_oku(request.POST.get('tarih'))
    if tarih is None:
        hatalar.append('%s sayım tarihini seç.' % etiket)
    elif not tz.sayim_tarihi_gecerli(tur, tarih, ay_ilk):
        hatalar.append('%s sayım tarihi %s için ayın %s yakın olmalı.' % (
            etiket, tz.ay_etiketi(ay_ilk), 'başına' if tur == 'ILK' else 'sonuna'))
    degerler = {}
    for u in urunler:
        parca = []
        for alan in ('koli', 'adet', 'acik'):
            if alan == 'acik' and not u.hacim:
                parca.append(None)
                continue
            ham = request.POST.get('%s_%d' % (alan, u.id))
            try:
                d = tz.sayi_oku(ham)
            except ValueError:
                hatalar.append('“%s” için geçersiz sayı: %s' % (u.ad, ham))
                d = None
            if d is not None and d < 0:
                hatalar.append('“%s” için eksi değer girilemez.' % u.ad)
                d = None
            parca.append(d)
        if any(x is not None for x in parca):
            degerler[u] = tuple(parca)
    if not degerler and not hatalar:
        hatalar.append('Hiç miktar girilmedi.')
    return hatalar, degerler, tarih


def temizlik_sayim(request, tur):
    """İlk / son sayım sayfası: koli + kapalı adet + açık kapta kalan miktar."""
    personel, ayar, git = _hazir(request)
    if git:
        return git
    if tur not in ('ilk', 'son'):
        return redirect('temizlik')
    TUR = 'ILK' if tur == 'ilk' else 'SON'
    subeler = tz.giris_subeleri(personel)
    if not subeler:
        return redirect('temizlik_rapor' if personel.rol in tz.RAPOR_ROLLERI else 'ana_sayfa')
    sid = request.POST.get('sube') or request.GET.get('sube') or ''
    sube = next((s for s in subeler if str(s.id) == sid), subeler[0])
    ay_ilk = _ay(request, ayar)
    urunler = list(TemizlikUrun.objects.filter(aktif=True))
    kayit = (TemizlikSayim.objects.filter(sube=sube, ay=ay_ilk, tur=TUR).prefetch_related('kalemler').first())
    onceki_deger = tz.sayim_degerleri(kayit)
    girilen = None
    tarih_deger = (kayit.tarih if kayit else (ay_ilk if TUR == 'ILK' else min(
        max(datetime.date.today(), ay_ilk), tz.ay_sonu(ay_ilk)))).strftime('%Y-%m-%d')

    if request.method == 'POST':
        hatalar, degerler, tarih = _sayim_oku(request, ay_ilk, TUR, urunler)
        if tz.baslamamis(ayar, ay_ilk):
            hatalar.insert(0, 'Sistem %s tarihinde başlıyor; %s için kayıt girilemez.' % (
                ayar.baslangic.strftime('%d.%m.%Y'), tz.ay_etiketi(ay_ilk)))
        diger = TemizlikSayim.objects.filter(sube=sube, ay=ay_ilk, tur=('SON' if TUR == 'ILK' else 'ILK')).first()
        if tarih and diger and ((TUR == 'ILK' and tarih >= diger.tarih) or (TUR == 'SON' and tarih <= diger.tarih)):
            hatalar.append('Son stok tarihi, ilk stok tarihinden sonra olmalı.')
        if hatalar:
            for h in hatalar[:6]:
                messages.error(request, h)
            girilen = {u.id: (request.POST.get('koli_%d' % u.id, ''), request.POST.get('adet_%d' % u.id, ''),
                              request.POST.get('acik_%d' % u.id, '')) for u in urunler}
            tarih_deger = request.POST.get('tarih', tarih_deger)
        else:
            with transaction.atomic():
                sy, _ = TemizlikSayim.objects.get_or_create(sube=sube, ay=ay_ilk, tur=TUR, defaults={'tarih': tarih})
                sy.tarih, sy.giren, sy.giren_ad = tarih, personel, personel.ad_soyad
                sy.save()
                sy.kalemler.all().delete()
                TemizlikSayimKalem.objects.bulk_create([
                    TemizlikSayimKalem(sayim=sy, urun=u, urun_ad=u.ad, koli=k, adet=a, acik=ac,
                                       miktar=tz.toplam_adet(u, k, a, ac)) for u, (k, a, ac) in degerler.items()])
            messages.success(request, '%s sayımı kaydedildi (%d ürün).' % (
                'İlk stok' if TUR == 'ILK' else 'Son stok', len(degerler)))
            return redirect(_ay_url(None, ay_ilk, sube))

    satirlar = []
    for u in urunler:
        if girilen is not None:
            k, a, ac = girilen[u.id]
        else:
            k, a, ac = (tz.girdi_yaz(x) for x in onceki_deger.get(u.id, (None, None, None)))
        satirlar.append({'urun': u, 'koli': k, 'adet': a, 'acik': ac})
    return render(request, 'temizlik_sayim.html', {
        'personel': personel, 'aktif': 'temizlik', 'tur': tur, 'tur_adi': 'İlk stok' if TUR == 'ILK' else 'Son stok',
        'sube': sube, 'subeler': subeler, 'ay_deger': ay_ilk.strftime('%Y-%m'), 'ay_etiket': tz.ay_etiketi(ay_ilk),
        'tarih': tarih_deger, 'satirlar': satirlar, 'var_mi': kayit is not None,
        'geri_url': _ay_url(None, ay_ilk, sube), **_ortak(personel, ayar, 'giris'),
    })


def _duzeltme_ekle(request, personel, sube, ay_ilk, veri_sube):
    urun = TemizlikUrun.objects.filter(id=request.POST.get('urun') or 0).first()
    tarih = _tarih_oku(request.POST.get('tarih'))
    try:
        miktar = tz.sayi_oku(request.POST.get('miktar'))
    except ValueError:
        miktar = None
    if urun is None or tarih is None or miktar is None or miktar == 0:
        messages.error(request, 'Düzeltme için ürün, tarih ve sıfırdan farklı bir miktar gerekli.')
        return
    if not (veri_sube['bas'] < tarih <= veri_sube['bit']):
        messages.error(request, 'Düzeltme tarihi, ilk sayımdan sonra ve %s tarihinden önce olmalı.' % (
            veri_sube['bit'].strftime('%d.%m.%Y')))
        return
    TemizlikDuzeltme.objects.create(sube=sube, ay=ay_ilk, urun=urun, urun_ad=urun.ad, tarih=tarih, miktar=miktar,
                                    aciklama=(request.POST.get('aciklama') or '').strip()[:200],
                                    giren=personel, giren_ad=personel.ad_soyad)
    messages.success(request, 'Düzeltme eklendi.')


def temizlik_giris(request):
    """Aylık çizelge (salt okunur) + düzeltme. Sayım ayrı sayfada girilir."""
    personel, ayar, git = _hazir(request)
    if git:
        return git
    subeler = tz.giris_subeleri(personel)
    if not subeler:
        return redirect('temizlik_rapor' if personel.rol in tz.RAPOR_ROLLERI else 'ana_sayfa')
    sid = request.POST.get('sube') or request.GET.get('sube') or ''
    sube = next((s for s in subeler if str(s.id) == sid), subeler[0])      # yetkisiz şube -> kendi şubesi
    ay_ilk = _ay(request, ayar)
    adres = _ay_url(None, ay_ilk, sube)

    if request.method == 'POST':
        islem = request.POST.get('islem', '')
        if islem == 'duzeltme_ekle':
            if tz.baslamamis(ayar, ay_ilk):
                messages.error(request, 'Sistem %s tarihinde başlıyor; %s için kayıt girilemez.' % (
                    ayar.baslangic.strftime('%d.%m.%Y'), tz.ay_etiketi(ay_ilk)))
            else:
                ham = tz.veri_hesapla([sube], ay_ilk)['subeler'][0]
                _duzeltme_ekle(request, personel, sube, ay_ilk, ham)
        elif islem == 'duzeltme_sil':
            sil = TemizlikDuzeltme.objects.filter(id=request.POST.get('id') or 0, sube=sube, ay=ay_ilk).first()
            if sil:
                sil.delete()
                messages.success(request, 'Düzeltme silindi.')
        return redirect(adres)

    veri = tz.veri_hesapla([sube], ay_ilk)
    c = veri['subeler'][0]
    haftalar = tz.hafta_parcalari(c['bas'], c['bit'])
    satirlar = []
    for r in c['satirlar']:
        if not r['urun'].aktif:
            continue
        r['hafta_degerleri'] = [tz.parca_toplam(r['gun_ilave'], h) for h in haftalar]
        satirlar.append(r)
    duzeltmeler = list(TemizlikDuzeltme.objects.filter(sube=sube, ay=ay_ilk).order_by('tarih', 'id'))
    onceki, sonraki = tz.ay_komsulari(ay_ilk)
    bugun = datetime.date.today()
    sayim_q = urlencode({'ay': ay_ilk.strftime('%Y-%m'), 'sube': sube.id})
    return render(request, 'temizlik_giris.html', {
        'personel': personel, 'aktif': 'temizlik', 'subeler': subeler, 'sube': sube,
        'ay_deger': ay_ilk.strftime('%Y-%m'), 'ay_etiket': veri['etiket'],
        'onceki_url': _ay_url(onceki, ay_ilk, sube), 'sonraki_url': _ay_url(sonraki, ay_ilk, sube),
        'c': c, 'haftalar': haftalar, 'satirlar': satirlar, 'duzeltmeler': duzeltmeler,
        'ilk_url': '%s?%s' % (reverse('temizlik_sayim', args=['ilk']), sayim_q),
        'son_url': '%s?%s' % (reverse('temizlik_sayim', args=['son']), sayim_q),
        'son_tarih': min(max(bugun, ay_ilk), tz.ay_sonu(ay_ilk)).strftime('%Y-%m-%d'),
        'rapor_gorebilir': personel.rol in tz.RAPOR_ROLLERI,
        'urun_duzenleyebilir': personel.rol in tz.URUN_ROLLERI,
        'eslesmeyen': veri['eslesmeyen'] if personel.rol in (tz.Rol.GENEL_MUDUR, tz.Rol.OPERATOR) else [],
        'urunler': [r['urun'] for r in satirlar], **_ortak(personel, ayar, 'giris'),
    })


def _urun_oku(request, mevcut=None):
    """Ürün formunu doğrular: (hata, alanlar)."""
    ad = ' '.join((request.POST.get('ad') or '').split())[:200]
    if not ad:
        return 'Ürün adı boş olamaz.', None
    sade_ad = tz.sade(ad)
    for u in TemizlikUrun.objects.all():
        if u.id != getattr(mevcut, 'id', None) and tz.sade(u.ad) == sade_ad:
            return '“%s” zaten listede var.' % u.ad, None
    birim = (request.POST.get('birim') or 'ADET').strip().upper()
    if birim not in tz.BIRIMLER:
        return 'Birim geçersiz.', None
    try:
        koli = tz.sayi_oku(request.POST.get('koli_icerigi'))
        if koli is None:
            koli = Decimal('1')
        hacim = tz.sayi_oku(request.POST.get('hacim'))
        sira = int(request.POST.get('sira') or 0)
    except (ValueError, TypeError):
        return 'Koli içeriği, kapasite ve sıra sayı olmalı.', None
    if koli <= 0 or (hacim is not None and hacim <= 0) or not (0 <= sira <= 100000):
        return 'Koli içeriği ve kapasite sıfırdan büyük olmalı.', None
    hacim_birim = (request.POST.get('hacim_birim') or '').strip().upper()
    if hacim is not None and hacim_birim not in tz.KAPASITE_BIRIMLERI:
        return 'Kapasite için birim seç (ml, lt, gr, kg).', None
    if hacim is None:
        hacim_birim = ''
    urun = Urun.objects.filter(id=request.POST.get('urun') or 0).first()
    return None, {'ad': ad, 'birim': birim, 'koli_icerigi': koli, 'hacim': hacim, 'hacim_birim': hacim_birim,
                  'urun': urun, 'sira': sira}


def temizlik_urunler(request):
    """Yönetici: temizlik ürünlerini ekle / düzenle / çıkar."""
    personel, ayar, git = _hazir(request)
    if git:
        return git
    if personel.rol not in tz.URUN_ROLLERI:
        return redirect('temizlik')
    if request.method == 'POST':
        islem = request.POST.get('islem', '')
        urun = TemizlikUrun.objects.filter(id=request.POST.get('id') or 0).first()
        if islem == 'ekle':
            hata, alan = _urun_oku(request)
            if hata:
                messages.error(request, hata)
            else:
                if not alan['sira']:
                    alan['sira'] = (TemizlikUrun.objects.order_by('-sira').values_list('sira', flat=True).first() or 0) + 1
                TemizlikUrun.objects.create(**alan)
                messages.success(request, '“%s” eklendi.' % alan['ad'])
        elif islem == 'kaydet' and urun:
            hata, alan = _urun_oku(request, urun)
            if hata:
                messages.error(request, hata)
            else:
                for k, v in alan.items():
                    setattr(urun, k, v)
                urun.save()
                messages.success(request, '“%s” güncellendi.' % urun.ad)
        elif islem == 'cikar' and urun:
            kullanildi = (TemizlikSayimKalem.objects.filter(urun=urun).exists()
                          or TemizlikDuzeltme.objects.filter(urun=urun).exists())
            if kullanildi:
                urun.aktif = False
                urun.save(update_fields=['aktif'])
                messages.success(request, '“%s” listeden çıkarıldı. Geçmiş sayımlar korundu; “Çıkarılanlar”dan geri alabilirsin.' % urun.ad)
            else:
                ad = urun.ad
                urun.delete()
                messages.success(request, '“%s” silindi.' % ad)
        elif islem == 'geri_al' and urun:
            urun.aktif = True
            urun.save(update_fields=['aktif'])
            messages.success(request, '“%s” listeye geri alındı.' % urun.ad)
        return redirect('temizlik_urunler')
    tum = list(TemizlikUrun.objects.all())
    return render(request, 'temizlik_urunler.html', {
        'personel': personel, 'aktif': 'temizlik',
        'aktifler': [u for u in tum if u.aktif], 'pasifler': [u for u in tum if not u.aktif],
        'katalog': list(Urun.objects.filter(aktif=True).order_by('form', 'ad')),
        'birimler': tz.BIRIMLER, 'kapasite_birimleri': tz.KAPASITE_BIRIMLERI, **_ortak(personel, ayar, 'urunler'),
    })


def _fiyat_oku(request, urunler, mevcut):
    """Fiyat formunu doğrular. (hatalar, degisenler[(urun, fiyat, birim)], girilen{urun_id: (fiyat, birim)})"""
    hatalar, degisen, girilen = [], [], {}
    for u in urunler:
        ham = (request.POST.get('fiyat_%d' % u.id) or '').strip()
        birim = (request.POST.get('birim_%d' % u.id) or 'ADET').strip().upper()
        girilen[u.id] = (ham, birim)
        if not ham:
            continue                      # boş = dokunma
        if birim not in ('ADET', 'KG', 'LT'):
            hatalar.append('“%s”: fiyat birimi geçersiz.' % u.ad)
            continue
        try:
            fiyat = tz.sayi_oku(ham)
        except ValueError:
            hatalar.append('“%s”: geçersiz fiyat (%s).' % (u.ad, ham))
            continue
        if fiyat is None or fiyat <= 0:
            hatalar.append('“%s”: fiyat sıfırdan büyük olmalı.' % u.ad)
            continue
        if not tz.fiyat_birimi_uygun(u, birim):
            hatalar.append('“%s”: %s fiyatı girilemez; önce Ürünler sayfasında kapasitesini (%s) tanımla.' % (
                u.ad, 'kg' if birim == 'KG' else 'litre', 'kg / gr' if birim == 'KG' else 'lt / ml'))
            continue
        eski = mevcut.get(u.id)
        if eski is None or eski['fiyat'] != fiyat or eski['birim'] != birim:
            degisen.append((u, fiyat, birim))
    return hatalar, degisen, girilen


def temizlik_fiyatlar(request):
    """Ürün fiyatları. Görenler: Satın Alma, Yatırımcı, Bölge Müdürü, Operatör, Genel Müdür. Yazanlar: Satın Alma, Genel Müdür."""
    personel, ayar, git = _hazir(request)
    if git:
        return git
    if not tz.fiyat_gorur(personel):
        return redirect('temizlik')
    yazar = tz.fiyat_yazar(personel)
    urunler = list(TemizlikUrun.objects.filter(aktif=True))
    mevcut = tz.fiyat_haritasi(None)
    girilen = None
    if request.method == 'POST':
        if not yazar:
            messages.error(request, 'Fiyatı yalnızca Satın Alma ve Genel Müdür girebilir.')
            return redirect('temizlik_fiyatlar')
        hatalar, degisen, girilen = _fiyat_oku(request, urunler, mevcut)
        if hatalar:
            for h in hatalar[:8]:
                messages.error(request, h)
        else:
            bugun = timezone.localdate()
            with transaction.atomic():
                for u, fiyat, birim in degisen:
                    TemizlikFiyat.objects.update_or_create(
                        urun=u, gecerli=bugun,
                        defaults={'fiyat': fiyat, 'birim': birim, 'giren_ad': personel.ad_soyad})
            messages.success(request, '%d ürünün fiyatı güncellendi.' % len(degisen) if degisen
                             else 'Değişen fiyat yok.')
            return redirect('temizlik_fiyatlar')
    satirlar = []
    for u in urunler:
        f = mevcut.get(u.id)
        if girilen is not None:
            fiyat_g, birim_g = girilen[u.id]
        else:
            fiyat_g, birim_g = (tz.girdi_yaz(f['fiyat']) if f else ''), (f['birim'] if f else 'ADET')
        satirlar.append({'urun': u, 'fiyat': fiyat_g, 'birim': birim_g, 'kayit': f,
                         'kg_uygun': tz.fiyat_birimi_uygun(u, 'KG'), 'lt_uygun': tz.fiyat_birimi_uygun(u, 'LT')})
    return render(request, 'temizlik_fiyatlar.html', {
        'personel': personel, 'aktif': 'temizlik', 'satirlar': satirlar, 'yazar': yazar,
        'fiyatsiz': sum(1 for r in satirlar if r['kayit'] is None), **_ortak(personel, ayar, 'fiyatlar'),
    })


def temizlik_ayarlar(request):
    """Sistemi aç/kapa, başlangıç tarihi, şube verisini sıfırla (Genel Müdür, Operatör)."""
    personel, ayar, git = _hazir(request)
    if git:
        return git
    if personel.rol not in tz.AYAR_ROLLERI:
        return redirect('temizlik')
    subeler = list(Sube.objects.filter(depo_mu=False).order_by('ad'))
    if request.method == 'POST':
        islem = request.POST.get('islem', '')
        if islem in ('ac', 'kapat'):
            ayar.aktif = islem == 'ac'
            ayar.guncelleyen = personel.ad_soyad
            ayar.save()
            messages.success(request, 'Temizlik sistemi açıldı. Şefler ve müdürler artık görebilir.' if ayar.aktif
                             else 'Temizlik sistemi kapatıldı. Şefler, müdürler ve yatırımcı göremez; kayıtlar korundu.')
        elif islem == 'baslangic':
            t = _tarih_oku(request.POST.get('baslangic'))
            if request.POST.get('baslangic', '').strip() == '':
                ayar.baslangic = None
                ayar.guncelleyen = personel.ad_soyad
                ayar.save()
                messages.success(request, 'Başlangıç tarihi kaldırıldı: tüm sevkiyatlar sayılır.')
            elif t is None:
                messages.error(request, 'Geçerli bir tarih seç.')
            else:
                ayar.baslangic = t
                ayar.guncelleyen = personel.ad_soyad
                ayar.save()
                messages.success(request, 'Başlangıç tarihi %s olarak kaydedildi.' % t.strftime('%d.%m.%Y'))
        elif islem == 'sifirla':
            hedef = request.POST.get('sube') or ''
            secili = next((s for s in subeler if str(s.id) == hedef), None)
            if (request.POST.get('onay') or '').strip().upper() != 'SIFIRLA':
                messages.error(request, 'Sıfırlamak için kutuya SIFIRLA yazmalısın.')
            elif hedef and secili is None:
                messages.error(request, 'Şube bulunamadı.')
            else:
                sy = TemizlikSayim.objects.all()
                dz = TemizlikDuzeltme.objects.all()
                if secili:
                    sy, dz = sy.filter(sube=secili), dz.filter(sube=secili)
                with transaction.atomic():
                    n_sy, n_dz = sy.count(), dz.count()
                    sy.delete()
                    dz.delete()
                    ayar.son_sifirlama = timezone.now()
                    ayar.son_sifirlayan = personel.ad_soyad
                    ayar.save()
                messages.success(request, '%s sıfırlandı: %d sayım ve %d düzeltme silindi. Sevkiyat kayıtları, ürün '
                                          'listesi ve fiyatlar olduğu gibi duruyor.' % (
                                              secili.ad if secili else 'Tüm şubeler', n_sy, n_dz))
        return redirect('temizlik_ayarlar')
    return render(request, 'temizlik_ayarlar.html', {
        'personel': personel, 'aktif': 'temizlik', 'subeler': subeler,
        'sayim_say': TemizlikSayim.objects.count(), 'duzeltme_say': TemizlikDuzeltme.objects.count(),
        'baslangic_deger': ayar.baslangic.strftime('%Y-%m-%d') if ayar.baslangic else '',
        **_ortak(personel, ayar, 'ayarlar'),
    })


def _rapor_hazirla(request):
    """(ctx, yanıt). ctx: personel, ayar, subeler, secili, gorunum, ay_ilk, veri."""
    personel, ayar, git = _hazir(request)
    if git:
        return None, git
    subeler = tz.rapor_subeleri(personel)
    if not subeler:
        return None, redirect('ana_sayfa')
    sid = request.GET.get('sube', '')
    secili = next((s for s in subeler if str(s.id) == sid), None)
    if secili is None and len(subeler) == 1:
        secili = subeler[0]
    gorunum = request.GET.get('gorunum', 'aylik')
    if gorunum not in dict(tz.GORUNUMLER):
        gorunum = 'aylik'
    ay_ilk = tz.ay_oku(request.GET.get('ay')) if request.GET.get('ay') else tz.varsayilan_ay(ayar)
    veri = tz.veri_hesapla([secili] if secili else subeler, ay_ilk, fiyatli=tz.fiyat_gorur(personel))
    return {'personel': personel, 'ayar': ayar, 'subeler': subeler, 'secili': secili, 'gorunum': gorunum,
            'ay_ilk': ay_ilk, 'veri': veri}, None


def temizlik_rapor(request):
    c, git = _rapor_hazirla(request)
    if git:
        return git
    personel, ayar, subeler, secili = c['personel'], c['ayar'], c['subeler'], c['secili']
    gorunum, ay_ilk, veri = c['gorunum'], c['ay_ilk'], c['veri']

    def url(taban, **ek):
        q = {'ay': ay_ilk.strftime('%Y-%m'), 'gorunum': gorunum}
        if secili and len(subeler) > 1:
            q['sube'] = secili.id
        q.update(ek)
        return '%s?%s' % (taban, urlencode(q))

    onceki, sonraki = tz.ay_komsulari(ay_ilk)
    parcalar = tz.takvim_parcalari(ay_ilk, gorunum) if gorunum != 'aylik' else []
    ilave_tablo, tuketim_tablo = [], []
    for r in veri['toplam']:
        if gorunum != 'aylik':
            ilave_tablo.append((r['urun'], [tz.parca_toplam(r['gun_ilave'], p) for p in parcalar]))
            tuketim_tablo.append((r['urun'], [tz.parca_toplam(r['gun_tuketim'], p) for p in parcalar]
                                  if r['gun_tuketim'] else None))
    rapor = reverse('temizlik_rapor_indir')
    giris_var = personel.rol in tz.GIRIS_ROLLERI and bool(tz.giris_subeleri(personel))
    return render(request, 'temizlik_rapor.html', {
        'personel': personel, 'aktif': 'temizlik', 'veri': veri, 'subeler': subeler, 'secili': secili,
        'coklu': len(subeler) > 1, 'gorunum': gorunum, 'gorunumler': tz.GORUNUMLER,
        'ay_deger': ay_ilk.strftime('%Y-%m'), 'ay_etiket': veri['etiket'],
        'onceki_url': url(reverse('temizlik_rapor'), ay=onceki.strftime('%Y-%m')),
        'sonraki_url': url(reverse('temizlik_rapor'), ay=sonraki.strftime('%Y-%m')),
        'parcalar': parcalar, 'ilave_tablo': ilave_tablo, 'tuketim_tablo': tuketim_tablo,
        'kirilim': tz.sube_kirilimi(veri) if (gorunum == 'aylik' and len(veri['subeler']) > 1) else [],
        'xlsx_url': url(rapor, bicim='xlsx'), 'pdf_url': url(rapor, bicim='pdf'),
        'giris_var': giris_var, 'urun_duzenleyebilir': personel.rol in tz.URUN_ROLLERI,
        'eslesmeyen': veri['eslesmeyen'] if personel.rol in (tz.Rol.GENEL_MUDUR, tz.Rol.OPERATOR) else [],
        **_ortak(personel, ayar, 'rapor'),
    })


def temizlik_rapor_indir(request):
    c, git = _rapor_hazirla(request)
    if git:
        return git
    secili, gorunum, ay_ilk, veri = c['secili'], c['gorunum'], c['ay_ilk'], c['veri']
    ad = 'temizlik_tuketimi_%s_%s%s' % (ay_ilk.strftime('%Y_%m'), gorunum, ('_sube%d' % secili.id) if secili else '')
    if request.GET.get('bicim') == 'pdf':
        y = HttpResponse(tz.pdf_bytes(veri, secili, gorunum), content_type='application/pdf')
        y['Content-Disposition'] = 'attachment; filename="%s.pdf"' % ad
    else:
        y = HttpResponse(tz.excel_bytes(veri, secili, gorunum),
                         content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        y['Content-Disposition'] = 'attachment; filename="%s.xlsx"' % ad
    return y
