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
from .models import TemizlikDuzeltme, TemizlikSayim, TemizlikSayimKalem, TemizlikUrun
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


def _sayim_kaydet(request, personel, sube, ay_ilk, tur):
    """tur: 'ILK' | 'SON'. Formdaki ilk_<id> / son_<id> kutularını kaydeder; hata varsa iletiyle döner."""
    onek = 'ilk_' if tur == 'ILK' else 'son_'
    etiket = 'İlk stok' if tur == 'ILK' else 'Son stok'
    tarih = _tarih_oku(request.POST.get(onek + 'tarih'))
    if tarih is None:
        messages.error(request, '%s sayım tarihini seç.' % etiket)
        return False
    if not tz.sayim_tarihi_gecerli(tur, tarih, ay_ilk):
        messages.error(request, '%s sayım tarihi %s için ayın %s yakın olmalı.' % (
            etiket, tz.ay_etiketi(ay_ilk), 'başına' if tur == 'ILK' else 'sonuna'))
        return False
    diger = TemizlikSayim.objects.filter(sube=sube, ay=ay_ilk, tur=('SON' if tur == 'ILK' else 'ILK')).first()
    if diger and ((tur == 'ILK' and tarih >= diger.tarih) or (tur == 'SON' and tarih <= diger.tarih)):
        messages.error(request, 'Son stok tarihi, ilk stok tarihinden sonra olmalı.')
        return False
    degerler = {}
    for u in TemizlikUrun.objects.filter(aktif=True):
        ham = request.POST.get('%s%d' % (onek, u.id))
        try:
            d = tz.sayi_oku(ham)
        except ValueError:
            messages.error(request, '“%s” için geçersiz sayı: %s' % (u.ad, ham))
            return False
        if d is not None:
            if d < 0:
                messages.error(request, '“%s” için eksi değer girilemez.' % u.ad)
                return False
            degerler[u] = d
    if not degerler:
        messages.error(request, 'Hiç miktar girilmedi.')
        return False
    with transaction.atomic():
        sy, _ = TemizlikSayim.objects.get_or_create(sube=sube, ay=ay_ilk, tur=tur, defaults={'tarih': tarih})
        sy.tarih, sy.giren, sy.giren_ad = tarih, personel, personel.ad_soyad
        sy.save()
        sy.kalemler.all().delete()
        TemizlikSayimKalem.objects.bulk_create([
            TemizlikSayimKalem(sayim=sy, urun=u, urun_ad=u.ad, miktar=d) for u, d in degerler.items()])
    messages.success(request, '%s sayımı kaydedildi (%d ürün).' % (etiket, len(degerler)))
    return True


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
        if islem in ('ilk', 'son'):
            _sayim_kaydet(request, personel, sube, ay_ilk, 'ILK' if islem == 'ilk' else 'SON')
        elif islem == 'duzeltme_ekle':
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
        r['ilk_girdi'] = tz.girdi_yaz(r['ilk'])
        r['son_girdi'] = tz.girdi_yaz(r['son'])
        satirlar.append(r)
    duzeltmeler = list(TemizlikDuzeltme.objects.filter(sube=sube, ay=ay_ilk).order_by('tarih', 'id'))
    onceki, sonraki = tz.ay_komsulari(ay_ilk)
    bugun = datetime.date.today()
    return render(request, 'temizlik_giris.html', {
        'personel': personel, 'aktif': 'temizlik', 'subeler': subeler, 'sube': sube,
        'ay_deger': ay_ilk.strftime('%Y-%m'), 'ay_etiket': veri['etiket'],
        'onceki_url': _ay_url(onceki, ay_ilk, sube), 'sonraki_url': _ay_url(sonraki, ay_ilk, sube),
        'c': c, 'haftalar': haftalar, 'satirlar': satirlar, 'duzeltmeler': duzeltmeler,
        'ilk_tarih': (c['ilk'].tarih if c['ilk'] else ay_ilk).strftime('%Y-%m-%d'),
        'son_tarih': (c['son'].tarih if c['son'] else min(max(bugun, ay_ilk), tz.ay_sonu(ay_ilk))).strftime('%Y-%m-%d'),
        'rapor_gorebilir': personel.rol in tz.RAPOR_ROLLERI,
        'eslesmeyen': veri['eslesmeyen'] if personel.rol in (tz.Rol.GENEL_MUDUR, tz.Rol.OPERATOR) else [],
        'urunler': [r['urun'] for r in satirlar],
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
        'giris_var': giris_var,
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
