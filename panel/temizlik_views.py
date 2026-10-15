"""Temizlik malzemesi tüketimi: sayım girişi (şef / mağaza müdürü) ve tüketim raporu (yönetim + şube)."""
import datetime
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from . import temizlik as tz
from .models import TemizlikDuzeltme, TemizlikSayim, TemizlikSayimKalem, TemizlikUrun, Urun
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


def temizlik_ana(request):
    """Menüdeki tek bağlantı: girebilen rol sayım sayfasına, diğerleri rapora gider."""
    personel, git = _personel(request)
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
    personel, git = _personel(request)
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
    ay_ilk = tz.ay_oku(request.POST.get('ay') or request.GET.get('ay'))
    urunler = list(TemizlikUrun.objects.filter(aktif=True))
    kayit = (TemizlikSayim.objects.filter(sube=sube, ay=ay_ilk, tur=TUR).prefetch_related('kalemler').first())
    onceki_deger = tz.sayim_degerleri(kayit)
    girilen = None
    tarih_deger = (kayit.tarih if kayit else (ay_ilk if TUR == 'ILK' else min(
        max(datetime.date.today(), ay_ilk), tz.ay_sonu(ay_ilk)))).strftime('%Y-%m-%d')

    if request.method == 'POST':
        hatalar, degerler, tarih = _sayim_oku(request, ay_ilk, TUR, urunler)
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
        'geri_url': _ay_url(None, ay_ilk, sube),
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
    personel, git = _personel(request)
    if git:
        return git
    subeler = tz.giris_subeleri(personel)
    if not subeler:
        return redirect('temizlik_rapor' if personel.rol in tz.RAPOR_ROLLERI else 'ana_sayfa')
    sid = request.POST.get('sube') or request.GET.get('sube') or ''
    sube = next((s for s in subeler if str(s.id) == sid), subeler[0])      # yetkisiz şube -> kendi şubesi
    ay_ilk = tz.ay_oku(request.POST.get('ay') or request.GET.get('ay'))
    adres = _ay_url(None, ay_ilk, sube)

    if request.method == 'POST':
        islem = request.POST.get('islem', '')
        if islem == 'duzeltme_ekle':
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
        'urunler': [r['urun'] for r in satirlar],
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
    personel, git = _personel(request)
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
        'birimler': tz.BIRIMLER, 'kapasite_birimleri': tz.KAPASITE_BIRIMLERI,
    })


def _rapor_hazirla(request):
    personel, git = _personel(request)
    if git:
        return None, None, None, None, None, None, git
    subeler = tz.rapor_subeleri(personel)
    if not subeler:
        return None, None, None, None, None, None, redirect('ana_sayfa')
    sid = request.GET.get('sube', '')
    secili = next((s for s in subeler if str(s.id) == sid), None)
    if secili is None and len(subeler) == 1:
        secili = subeler[0]
    gorunum = request.GET.get('gorunum', 'aylik')
    if gorunum not in dict(tz.GORUNUMLER):
        gorunum = 'aylik'
    ay_ilk = tz.ay_oku(request.GET.get('ay'))
    veri = tz.veri_hesapla([secili] if secili else subeler, ay_ilk)
    return personel, subeler, secili, gorunum, ay_ilk, veri, None


def temizlik_rapor(request):
    personel, subeler, secili, gorunum, ay_ilk, veri, git = _rapor_hazirla(request)
    if git:
        return git

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
    })


def temizlik_rapor_indir(request):
    personel, subeler, secili, gorunum, ay_ilk, veri, git = _rapor_hazirla(request)
    if git:
        return git
    ad = 'temizlik_tuketimi_%s_%s%s' % (ay_ilk.strftime('%Y_%m'), gorunum, ('_sube%d' % secili.id) if secili else '')
    if request.GET.get('bicim') == 'pdf':
        y = HttpResponse(tz.pdf_bytes(veri, secili, gorunum), content_type='application/pdf')
        y['Content-Disposition'] = 'attachment; filename="%s.pdf"' % ad
    else:
        y = HttpResponse(tz.excel_bytes(veri, secili, gorunum),
                         content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        y['Content-Disposition'] = 'attachment; filename="%s.xlsx"' % ad
    return y
