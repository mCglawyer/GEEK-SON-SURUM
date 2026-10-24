"""Menulux satış raporları: yatırımcı / genel müdür / operatör / bölge müdürü / şef."""
import datetime
import logging

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from . import menulux as mx
from . import satis_cikti as sc
from . import tuketim as tk
from .models import Rol, Sube
from .views import _aktif_personel, _cikis_mi, _logout

log = logging.getLogger(__name__)
TUM_ROLLER = (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI)        # tüm Menulux şubelerini görür
OLCEKLI_ROLLER = (Rol.MUDUR, Rol.MAGAZA_MUDURU, Rol.SEF)           # yalnızca eşleşmiş kendi şubeleri
RAPOR_ROLLERI = TUM_ROLLER + OLCEKLI_ROLLER
ESLESTIRME_ROLLERI = (Rol.GENEL_MUDUR, Rol.OPERATOR)

DONEMLER = [('bugun', 'Bugün'), ('dun', 'Dün'), ('hafta', 'Bu hafta'), ('gecen_hafta', 'Geçen hafta'),
            ('ay', 'Bu ay'), ('gecen_ay', 'Geçen ay'), ('ozel', 'Özel aralık')]


def satis_gorunur(personel):
    return personel is not None and personel.rol in RAPOR_ROLLERI


def _hazir(request, roller=RAPOR_ROLLERI):
    if not request.user.is_authenticated:
        return None, redirect('ana_sayfa')
    if _cikis_mi(request):
        return None, _logout(request)
    p = _aktif_personel(request)
    if p is None or p.rol not in roller:
        return None, redirect('ana_sayfa')
    return p, None


def _tarih(metin):
    try:
        return datetime.date.fromisoformat(metin) if metin else None
    except ValueError:
        return None


def donem_oku(donem, bas=None, bit=None, bugun=None):
    bugun = bugun or timezone.localdate()
    if donem == 'dun':
        d = bugun - datetime.timedelta(days=1); return d, d
    if donem == 'hafta':
        b = bugun - datetime.timedelta(days=bugun.weekday()); return b, bugun
    if donem == 'gecen_hafta':
        b = bugun - datetime.timedelta(days=bugun.weekday() + 7); return b, b + datetime.timedelta(days=6)
    if donem == 'ay':
        return bugun.replace(day=1), bugun
    if donem == 'gecen_ay':
        son = bugun.replace(day=1) - datetime.timedelta(days=1); return son.replace(day=1), son
    if donem == 'ozel' and bas and bit:
        if bit < bas:
            bas, bit = bit, bas
        return bas, min(bit, bas + datetime.timedelta(days=366))
    return bugun, bugun


def kapsam_secenekleri(personel):
    """(secenekler, hata). secenek: (deger, etiket, kimlik listesi | 'tum')."""
    if personel.rol in TUM_ROLLER:
        try:
            liste = mx.subeler()
        except mx.MenuluxHata as e:
            return [], str(e)
        return [('tum', 'Tüm şubeler (toplam)', 'tum')] + [(str(b['id']), b['ad'], [b['id']]) for b in liste], ''
    subeler = [s for s in tk.rapor_subeleri(personel) if s.menulux_id]
    secenekler = [(str(s.menulux_id), s.ad, [s.menulux_id]) for s in subeler]
    if len(subeler) > 1:
        secenekler.insert(0, ('tum', 'Tüm sorumlu şubelerim', [s.menulux_id for s in subeler]))
    return secenekler, ''


def _rapor_verisi(request, personel, urunler=True):
    donem = request.GET.get('donem') or 'bugun'
    bas, bit = donem_oku(donem, _tarih(request.GET.get('bas')), _tarih(request.GET.get('bit')))
    secenekler, hata = kapsam_secenekleri(personel)
    secili = next((s for s in secenekler if s[0] == (request.GET.get('sube') or '')), secenekler[0] if secenekler else None)
    ctx = {'donemler': DONEMLER, 'donem': donem, 'bas': bas, 'bit': bit, 'secenekler': secenekler, 'secili': secili,
           'hata': hata, 'veri': None, 'personel': personel, 'aktif': 'satis',
           'etiket': bas.strftime('%d.%m.%Y') if bas == bit else '%s – %s' % (bas.strftime('%d.%m.%Y'), bit.strftime('%d.%m.%Y'))}
    if secili and not hata:
        try:
            ctx['veri'] = mx.rapor(secili[2], bas, bit, urunler=urunler)
        except mx.MenuluxHata as e:
            ctx['hata'] = str(e)
        except Exception:
            log.exception('Satış raporu')
            ctx['hata'] = 'Rapor hazırlanırken beklenmeyen bir hata oluştu.'
    return ctx


def satis_rapor(request):
    personel, git = _hazir(request)
    if git:
        return git
    if not mx.ayarli_mi():
        return render(request, 'satis_rapor.html', {'personel': personel, 'aktif': 'satis', 'kapali': True,
                                                    'eslestirme_gorur': personel.rol in ESLESTIRME_ROLLERI})
    ctx = _rapor_verisi(request, personel)
    ctx['eslestirme_gorur'] = personel.rol in ESLESTIRME_ROLLERI
    ctx['eslesme_yok'] = personel.rol in OLCEKLI_ROLLER and not ctx['secenekler']
    return render(request, 'satis_rapor.html', ctx)


def satis_indir(request):
    personel, git = _hazir(request)
    if git:
        return git
    if not mx.ayarli_mi():
        return redirect('satis_rapor')
    ctx = _rapor_verisi(request, personel)
    if ctx['veri'] is None:
        messages.error(request, ctx['hata'] or 'Rapor oluşturulamadı.')
        return redirect('satis_rapor')
    pdf = request.GET.get('bicim') == 'pdf'
    sube_adi = ctx['secili'][1]
    govde = (sc.pdf_bytes if pdf else sc.excel_bytes)(ctx['veri'], ctx['etiket'], sube_adi)
    ad = 'satis_%s_%s_%s' % (ctx['secili'][0], ctx['bas'].strftime('%Y%m%d'), ctx['bit'].strftime('%Y%m%d'))
    y = HttpResponse(govde, content_type='application/pdf' if pdf else
                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    y['Content-Disposition'] = 'attachment; filename="%s.%s"' % (ad, 'pdf' if pdf else 'xlsx')
    return y


def satis_eslestirme(request):
    """Panel şubesi ↔ Menulux şubesi eşleştirmesi (bölge müdürü / şef yetkisi buna dayanır)."""
    personel, git = _hazir(request, ESLESTIRME_ROLLERI)
    if git:
        return git
    if not mx.ayarli_mi():
        return redirect('satis_rapor')
    try:
        mx_subeler = mx.subeler()
    except mx.MenuluxHata as e:
        messages.error(request, str(e))
        return redirect('satis_rapor')
    panel_subeleri = list(Sube.objects.filter(depo_mu=False).order_by('ad'))
    gecerli = {b['id'] for b in mx_subeler}
    if request.method == 'POST':
        secim, kullanilan, hata = {}, set(), False
        for s in panel_subeleri:
            ham = (request.POST.get('s%d' % s.id) or '').strip()
            if not ham:
                secim[s.id] = None; continue
            try:
                n = int(ham)
            except ValueError:
                continue
            if n not in gecerli or n in kullanilan:
                hata = True; messages.error(request, '%s: şube numarası geçersiz ya da başka bir şubeye atanmış.' % s.ad); continue
            kullanilan.add(n); secim[s.id] = n
        if not hata:
            # unique kısıtı için önce hepsini boşalt
            Sube.objects.filter(id__in=list(secim)).update(menulux_id=None)
            for sid, n in secim.items():
                if n:
                    Sube.objects.filter(id=sid).update(menulux_id=n)
            messages.success(request, 'Şube eşleştirmesi kaydedildi.')
            return redirect('satis_eslestirme')
    oneri = mx.eslestirme_onerisi([s for s in panel_subeleri if not s.menulux_id], mx_subeler)
    satirlar = [{'sube': s, 'secili': s.menulux_id, 'oneri': oneri.get(s.id)} for s in panel_subeleri]
    kullanimda = {s.menulux_id for s in panel_subeleri if s.menulux_id}
    eslesmeyen = [b for b in mx_subeler if b['id'] not in kullanimda]
    return render(request, 'satis_eslestirme.html', {'personel': personel, 'aktif': 'satis', 'satirlar': satirlar,
                                                     'mx_subeler': mx_subeler, 'eslesmeyen': eslesmeyen})
