"""Sevkiyat analizi ekranı ve Excel / PDF raporu (ay bazında, şube + ürün kırılımı)."""
from urllib.parse import urlencode

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from . import sevkiyat_analiz as sa
from .views import _aktif_personel, _cikis_mi, _logout


def _hazirla(request):
    """(personel, subeler, secili_sube, ay_ilk, yönlendirme)"""
    if not request.user.is_authenticated:
        return None, None, None, None, redirect('ana_sayfa')
    if _cikis_mi(request):
        return None, None, None, None, _logout(request)
    personel = _aktif_personel(request)
    if personel is None:
        return None, None, None, None, redirect('ana_sayfa')
    subeler = sa.analiz_subeleri(personel)
    if personel.rol not in sa.ANALIZ_ROLLERI:
        return None, None, None, None, redirect('ana_sayfa')
    sid = request.GET.get('sube', '')
    secili = next((s for s in subeler if str(s.id) == sid), None)   # yetkisiz / bozuk şube -> tümü
    return personel, subeler, secili, sa.ay_oku(request.GET.get('ay')), None


def sevkiyat_analiz(request):
    personel, subeler, secili, ay_ilk, git = _hazirla(request)
    if git:
        return git
    veri = sa.analiz_verisi(ay_ilk, subeler)
    g = sa.gorunum(veri, secili, urun_anahtar=request.GET.get('urun'))
    onceki, sonraki = sa.ay_komsulari(ay_ilk)

    def url(ad, **ek):
        q = {'ay': ad.strftime('%Y-%m') if ad else ay_ilk.strftime('%Y-%m')}
        if secili:
            q['sube'] = secili.id
        q.update(ek)
        return '%s?%s' % (reverse('sevkiyat_analiz'), urlencode(q))

    rapor = reverse('sevkiyat_analiz_rapor')
    rq = {'ay': ay_ilk.strftime('%Y-%m')}
    if secili:
        rq['sube'] = secili.id
    return render(request, 'sevkiyat_analiz.html', {
        'personel': personel, 'aktif': 'sevkiyat', 'veri': veri, 'subeler': subeler, 'secili': secili,
        'ay_deger': ay_ilk.strftime('%Y-%m'), 'ay_etiket': veri['etiket'],
        'onceki_url': url(onceki), 'sonraki_url': url(sonraki),
        'satirlar': g['satirlar'], 'grafik_urun': g['grafik_urun'], 'grafik_sube': g['grafik_sube'],
        'secili_urun': g['secili_urun'],
        'xlsx_url': '%s?%s' % (rapor, urlencode(dict(rq, bicim='xlsx'))),
        'pdf_url': '%s?%s' % (rapor, urlencode(dict(rq, bicim='pdf'))),
    })


def sevkiyat_analiz_rapor(request):
    personel, subeler, secili, ay_ilk, git = _hazirla(request)
    if git:
        return git
    veri = sa.analiz_verisi(ay_ilk, subeler)
    ad = 'sevkiyat_analizi_%s%s' % (ay_ilk.strftime('%Y_%m'), ('_sube%d' % secili.id) if secili else '')
    bicim = request.GET.get('bicim', '')
    if bicim == 'xlsx':
        y = HttpResponse(sa.excel_bytes(veri, secili),
                         content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        y['Content-Disposition'] = 'attachment; filename="%s.xlsx"' % ad
        return y
    if bicim == 'pdf':
        y = HttpResponse(sa.pdf_bytes(veri, secili), content_type='application/pdf')
        y['Content-Disposition'] = 'attachment; filename="%s.pdf"' % ad
        return y
    return redirect('sevkiyat_analiz')
