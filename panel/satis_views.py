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
from .models import KategoriGrubu, Rol, Sube
from .views import _aktif_personel, _cikis_mi, _logout

log = logging.getLogger(__name__)
TUM_ROLLER = (Rol.GENEL_MUDUR, Rol.OPERATOR, Rol.YATIRIMCI, Rol.SATIN_ALMA)  # tüm Menulux şubelerini görür
OLCEKLI_ROLLER = (Rol.MUDUR, Rol.MAGAZA_MUDURU, Rol.SEF)           # yalnızca eşleşmiş kendi şubeleri
RAPOR_ROLLERI = TUM_ROLLER + OLCEKLI_ROLLER
ESLESTIRME_ROLLERI = (Rol.GENEL_MUDUR, Rol.OPERATOR)

# Satış raporları artık kendi "paneli" gibi: ortak üst çubuk + hamburger menüsüyle geziliyor (bkz. _satis_panelbar.html).
SR_SAYFA = {'satis_rapor.html': 'rapor', 'satis_ozet.html': 'ozet', 'satis_tablo.html': 'tablo',
            'satis_ikram_iptal.html': 'ikram_iptal', 'satis_eslestirme.html': 'eslestirme',
            'satis_kategori_gruplari.html': 'kategori'}


def _sr_render(request, template, ctx):
    """satis_*.html şablonlarını ortak panel çubuğu bağlamıyla (rapor_panel/sr_aktif/eslestirme_gorur) render eder."""
    ctx = dict(ctx)
    ctx['rapor_panel'] = True
    ctx['sr_aktif'] = SR_SAYFA.get(template, '')
    personel = ctx.get('personel')
    ctx.setdefault('eslestirme_gorur', bool(personel) and personel.rol in ESLESTIRME_ROLLERI)
    return render(request, template, ctx)

DONEMLER = [('bugun', 'Bugün'), ('dun', 'Dün'), ('hafta', 'Bu hafta'), ('gecen_hafta', 'Geçen hafta'),
            ('ay', 'Bu ay'), ('gecen_ay', 'Geçen ay'), ('ozel', 'Özel aralık')]

AY_ADLARI = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
AY_KISA = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']


def hafta_araliklari(ref):
    """4 haftalık tablo: en eski haftadan (1) içinde ref olan haftaya (4) kadar, Pazartesi–Pazar."""
    bu_hafta = ref - datetime.timedelta(days=ref.weekday())
    return [(bu_hafta - datetime.timedelta(weeks=3 - i), bu_hafta - datetime.timedelta(weeks=3 - i) + datetime.timedelta(days=6)) for i in range(4)]


def ay_araliklari(yil):
    """Ocak–Aralık (yil) için (ayın ilk günü, son günü) listesi."""
    cikti = []
    for ay in range(1, 13):
        b = datetime.date(yil, ay, 1)
        e = (b.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
        cikti.append((b, e))
    return cikti


def _kategori_matrisi(kategori_liste, anahtar):
    """kategori_liste: her dönem için kategorileri_birlestir() çıktısı. Kategori adına göre dönem dönem değer satırları, toplama göre sıralı."""
    toplamlar = {}
    for donem in kategori_liste:
        for k in donem:
            toplamlar[k['ad']] = toplamlar.get(k['ad'], 0) + k[anahtar]
    satirlar = []
    for ad in sorted(toplamlar, key=lambda a: -toplamlar[a]):
        degerler = [next((k[anahtar] for k in donem if k['ad'] == ad), 0) for donem in kategori_liste]
        satirlar.append({'ad': ad, 'degerler': degerler, 'toplam': sum(degerler)})
    return satirlar


def _norm(s):
    return (s or '').strip().casefold()


def _kategori_haritasi():
    """{ham_kategori_adi (normalize edilmiş): grup_adi} — Genel Müdür/Operatör'ün tanımladığı
    kalıcı kategori birleştirmelerinin (KategoriGrubu) düz haritası."""
    harita = {}
    for g in KategoriGrubu.objects.all():
        for uye in (g.uyeler or []):
            harita[_norm(uye)] = g.ad
    return harita


def _kategorileri_grupla(liste, harita=None):
    """kategorileri_birlestir() çıktısı gibi [{'ad','adet','net','kdv','tutar'}] listesini, tanımlı
    KategoriGrubu eşleştirmelerine göre birleştirir. Eşleşmeyen kategoriler olduğu gibi kalır."""
    if harita is None:
        harita = _kategori_haritasi()
    if not harita or not liste:
        return liste
    toplam = {}
    for k in liste:
        grup = harita.get(_norm(k.get('ad')), k.get('ad'))
        if grup not in toplam:
            toplam[grup] = dict(k); toplam[grup]['ad'] = grup
        else:
            t = toplam[grup]
            for alan in ('adet', 'net', 'kdv', 'tutar'):
                if alan in k:
                    t[alan] = t.get(alan, 0) + (k.get(alan) or 0)
    return sorted(toplam.values(), key=lambda x: -x.get('tutar', 0))


def _urunleri_sirala(urunler, siralama):
    if siralama == 'kategori':
        return sorted(urunler, key=lambda u: (u.get('grup') or '', -(u.get('tutar') or 0)))
    return urunler


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
    siralama = request.GET.get('siralama') if request.GET.get('siralama') in ('adet', 'kategori') else 'adet'
    ctx['siralama'] = siralama
    if secili and not hata:
        try:
            veri = mx.rapor(secili[2], bas, bit, urunler=urunler)
            if veri.get('kategoriler'):
                veri['kategoriler'] = _kategorileri_grupla(veri['kategoriler'])
            if veri.get('urunler'):
                veri['urunler'] = _urunleri_sirala(veri['urunler'], siralama)
            ctx['veri'] = veri
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
        return _sr_render(request, 'satis_rapor.html', {'personel': personel, 'aktif': 'satis', 'kapali': True,
                                                    'eslestirme_gorur': personel.rol in ESLESTIRME_ROLLERI})
    ctx = _rapor_verisi(request, personel)
    ctx['eslestirme_gorur'] = personel.rol in ESLESTIRME_ROLLERI
    ctx['eslesme_yok'] = personel.rol in OLCEKLI_ROLLER and not ctx['secenekler']
    return _sr_render(request, 'satis_rapor.html', ctx)


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


def _tablo_ctx(request, personel):
    """satis_tablo ve satis_tablo_indir'in paylaştığı veri hazırlama (Haftalık / aylık tablo görünümü)."""
    secenekler, hata = kapsam_secenekleri(personel)
    secili = next((s for s in secenekler if s[0] == (request.GET.get('sube') or '')), secenekler[0] if secenekler else None)
    gorunum = 'ay' if request.GET.get('gorunum') == 'ay' else 'hafta'
    ctx = {'personel': personel, 'aktif': 'satis', 'secenekler': secenekler, 'secili': secili, 'hata': hata,
           'gorunum': gorunum, 'eslesme_yok': personel.rol in OLCEKLI_ROLLER and not secenekler}
    if secili and not hata:
        try:
            ana = secili[0] == 'tum'
            ana_no = mx.ana_id()
            idler = [ana_no] if ana else secili[2]
            adlar = {b['id']: b['ad'] for b in mx.subeler()}
            sube_ids = list(adlar) if ana else idler
            kirilim_ids = sube_ids if (ana or len(idler) > 1) else []
            if gorunum == 'ay':
                bugun = timezone.localdate()
                yil = int(request.GET.get('yil') or bugun.year)
                aylar = ay_araliklari(yil)
                varsayilan = bugun.month if yil == bugun.year else 12
                secili_no = min(max(int(request.GET.get('ay') or varsayilan), 1), 12)
                secili_bas, secili_bit = aylar[secili_no - 1]
                # Özet (12 ay) + kategori (12 ay, matris için) + şube kırılımı (seçili ay) — TEK coklu() dalgasında.
                ozetler, kategori_liste, sube_kirilim = mx.tablo_verisi(
                    idler, aylar, aylar, ana_no, kirilim_ids, (secili_bas, secili_bit), adlar)
                harita = _kategori_haritasi()
                kategori_liste = [_kategorileri_grupla(k, harita) for k in kategori_liste]
                kategori_secili = kategori_liste[secili_no - 1]
                ctx['kategori_matris_tutar'] = _kategori_matrisi(kategori_liste, 'tutar')
                ctx['kategori_matris_adet'] = _kategori_matrisi(kategori_liste, 'adet')
                ctx['ay_kisa'] = AY_KISA
                donem_satirlari = [{'etiket': AY_ADLARI[i], 'no': i + 1, 'ozet': ozetler[i], 'secili': i + 1 == secili_no} for i in range(12)]
                ctx.update(yil=yil, donem_etiket='%s %s' % (AY_ADLARI[secili_no - 1], yil))
            else:
                ref = _tarih(request.GET.get('ref')) or timezone.localdate()
                haftalar = hafta_araliklari(ref)
                secili_no = min(max(int(request.GET.get('hafta') or 4), 1), 4)
                secili_bas, secili_bit = haftalar[secili_no - 1]
                # Özet (4 hafta) + kategori (yalnız seçili hafta) + şube kırılımı (seçili hafta) — TEK coklu() dalgasında.
                ozetler, kategori_liste, sube_kirilim = mx.tablo_verisi(
                    idler, haftalar, [(secili_bas, secili_bit)], ana_no, kirilim_ids, (secili_bas, secili_bit), adlar)
                kategori_secili = _kategorileri_grupla(kategori_liste[0])
                donem_satirlari = [{'etiket': '%d. Hafta' % (i + 1), 'aralik': '%s – %s' % (b.strftime('%d.%m'), e.strftime('%d.%m')),
                                    'no': i + 1, 'ozet': ozetler[i], 'secili': i + 1 == secili_no} for i, (b, e) in enumerate(haftalar)]
                ctx.update(ref=ref, ref_onceki=ref - datetime.timedelta(weeks=4), ref_sonraki=ref + datetime.timedelta(weeks=4),
                          donem_etiket='%s – %s' % (secili_bas.strftime('%d.%m.%Y'), secili_bit.strftime('%d.%m.%Y')))
            toplam_kat = sum(k['tutar'] for k in kategori_secili) or 1
            for k in kategori_secili:
                k['pay'] = k['tutar'] / toplam_kat * 100
            toplam = mx.ozetleri_topla([d['ozet'] for d in donem_satirlari]); toplam['ort'] = mx.ortalama(toplam)
            ctx.update(donem_satirlari=donem_satirlari, toplam=toplam, secili_ozet=ozetler[secili_no - 1], secili_no=secili_no,
                       kategori=kategori_secili, subeler=sube_kirilim)
        except mx.MenuluxHata as e:
            ctx['hata'] = str(e)
        except Exception:
            log.exception('Satış tablosu')
            ctx['hata'] = 'Tablo hazırlanırken beklenmeyen bir hata oluştu.'
    return ctx


def satis_tablo(request):
    """Haftalık / aylık tablo görünümü (Google Sheets şablonlarındaki düzen: seç + dönem tablosu + şube + kategori)."""
    personel, git = _hazir(request)
    if git:
        return git
    if not mx.ayarli_mi():
        return _sr_render(request, 'satis_tablo.html', {'personel': personel, 'aktif': 'satis', 'kapali': True})
    return _sr_render(request, 'satis_tablo.html', _tablo_ctx(request, personel))


def satis_tablo_indir(request):
    personel, git = _hazir(request)
    if git:
        return git
    if not mx.ayarli_mi():
        return redirect('satis_tablo')
    ctx = _tablo_ctx(request, personel)
    if not ctx.get('donem_satirlari'):
        messages.error(request, ctx.get('hata') or 'Tablo oluşturulamadı.')
        return redirect('satis_tablo')
    pdf = request.GET.get('bicim') == 'pdf'
    sube_adi = ctx['secili'][1]
    govde = (sc.tablo_pdf_bytes if pdf else sc.tablo_excel_bytes)(ctx, ctx['donem_etiket'], sube_adi)
    ad = 'satis_tablo_%s_%s' % (ctx['secili'][0], ctx['donem_etiket'].replace(' ', '_').replace('.', '').replace('–', '-'))
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
    return _sr_render(request, 'satis_eslestirme.html', {'personel': personel, 'aktif': 'satis', 'satirlar': satirlar,
                                                     'mx_subeler': mx_subeler, 'eslesmeyen': eslesmeyen})


def _ikram_iptal_ctx(request, personel):
    donem = request.GET.get('donem') or 'bugun'
    bas, bit = donem_oku(donem, _tarih(request.GET.get('bas')), _tarih(request.GET.get('bit')))
    secenekler, hata = kapsam_secenekleri(personel)
    secili = next((s for s in secenekler if s[0] == (request.GET.get('sube') or '')), secenekler[0] if secenekler else None)
    sekme = request.GET.get('sekme') if request.GET.get('sekme') in ('ikram', 'iptal', 'iade') else 'ikram'
    ctx = {'donemler': DONEMLER, 'donem': donem, 'bas': bas, 'bit': bit, 'secenekler': secenekler, 'secili': secili,
           'hata': hata, 'personel': personel, 'aktif': 'satis', 'veri': None, 'sekme': sekme,
           'eslesme_yok': personel.rol in OLCEKLI_ROLLER and not secenekler,
           'etiket': bas.strftime('%d.%m.%Y') if bas == bit else '%s – %s' % (bas.strftime('%d.%m.%Y'), bit.strftime('%d.%m.%Y'))}
    if secili and not hata:
        try:
            ana = secili[0] == 'tum'
            adlar = {b['id']: b['ad'] for b in mx.subeler()}
            idler = list(adlar) if ana else secili[2]
            ctx['veri'] = mx.ikram_iptal(idler, bas, bit, adlar)
        except mx.MenuluxHata as e:
            ctx['hata'] = str(e)
        except Exception:
            log.exception('İkram/iptal/iade detayı')
            ctx['hata'] = 'Detay hazırlanırken beklenmeyen bir hata oluştu.'
    return ctx


def satis_ikram_iptal(request):
    """İkram / iptal / iade detayı: hangi üründe, kime/ne sebeple, hangi personel tarafından."""
    personel, git = _hazir(request)
    if git:
        return git
    if not mx.ayarli_mi():
        return _sr_render(request, 'satis_ikram_iptal.html', {'personel': personel, 'aktif': 'satis', 'kapali': True})
    return _sr_render(request, 'satis_ikram_iptal.html', _ikram_iptal_ctx(request, personel))


def satis_ikram_iptal_indir(request):
    personel, git = _hazir(request)
    if git:
        return git
    if not mx.ayarli_mi():
        return redirect('satis_ikram_iptal')
    ctx = _ikram_iptal_ctx(request, personel)
    if ctx.get('veri') is None:
        messages.error(request, ctx.get('hata') or 'Detay oluşturulamadı.')
        return redirect('satis_ikram_iptal')
    pdf = request.GET.get('bicim') == 'pdf'
    sube_adi = ctx['secili'][1]
    govde = (sc.ikram_iptal_pdf_bytes if pdf else sc.ikram_iptal_excel_bytes)(ctx['veri'], ctx['etiket'], sube_adi)
    ad = 'ikram_iptal_iade_%s_%s_%s' % (ctx['secili'][0], ctx['bas'].strftime('%Y%m%d'), ctx['bit'].strftime('%Y%m%d'))
    y = HttpResponse(govde, content_type='application/pdf' if pdf else
                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    y['Content-Disposition'] = 'attachment; filename="%s.%s"' % (ad, 'pdf' if pdf else 'xlsx')
    return y


def _ozet_ctx(request, personel):
    donem = request.GET.get('donem') or 'hafta'
    bas, bit = donem_oku(donem, _tarih(request.GET.get('bas')), _tarih(request.GET.get('bit')))
    secenekler, hata = kapsam_secenekleri(personel)
    secili = next((s for s in secenekler if s[0] == (request.GET.get('sube') or '')), secenekler[0] if secenekler else None)
    siralama = request.GET.get('siralama') if request.GET.get('siralama') in ('adet', 'kategori') else 'adet'
    ctx = {'donemler': DONEMLER, 'donem': donem, 'bas': bas, 'bit': bit, 'secenekler': secenekler, 'secili': secili,
           'hata': hata, 'personel': personel, 'aktif': 'satis', 'veri': None, 'siralama': siralama,
           'eslesme_yok': personel.rol in OLCEKLI_ROLLER and not secenekler,
           'etiket': bas.strftime('%d.%m.%Y') if bas == bit else '%s – %s' % (bas.strftime('%d.%m.%Y'), bit.strftime('%d.%m.%Y'))}
    if secili and not hata:
        try:
            veri = mx.ozet_verisi(secili[2], bas, bit)
            if veri.get('kategoriler'):
                veri['kategoriler'] = _kategorileri_grupla(veri['kategoriler'])
            if veri.get('urunler'):
                veri['urunler'] = _urunleri_sirala(veri['urunler'], siralama)
            ctx['veri'] = veri
        except mx.MenuluxHata as e:
            ctx['hata'] = str(e)
        except Exception:
            log.exception('Satış özeti')
            ctx['hata'] = 'Özet hazırlanırken beklenmeyen bir hata oluştu.'
    return ctx


def satis_ozet(request):
    """Menulux'un kendi 'Rapor Özeti' (Customer/ReportSummary) sayfasının panele taşınmış hâli:
    KPI kartları, ödeme/kategori/kanal/şube grafikleri, günlük ciro grafiği, en çok satan ürünler."""
    personel, git = _hazir(request)
    if git:
        return git
    if not mx.ayarli_mi():
        return _sr_render(request, 'satis_ozet.html', {'personel': personel, 'aktif': 'satis', 'kapali': True})
    return _sr_render(request, 'satis_ozet.html', _ozet_ctx(request, personel))


def satis_ozet_indir(request):
    personel, git = _hazir(request)
    if git:
        return git
    if not mx.ayarli_mi():
        return redirect('satis_ozet')
    ctx = _ozet_ctx(request, personel)
    if ctx.get('veri') is None:
        messages.error(request, ctx.get('hata') or 'Özet oluşturulamadı.')
        return redirect('satis_ozet')
    pdf = request.GET.get('bicim') == 'pdf'
    sube_adi = ctx['secili'][1]
    govde = (sc.ozet_pdf_bytes if pdf else sc.ozet_excel_bytes)(ctx['veri'], ctx['etiket'], sube_adi)
    ad = 'rapor_ozeti_%s_%s_%s' % (ctx['secili'][0], ctx['bas'].strftime('%Y%m%d'), ctx['bit'].strftime('%Y%m%d'))
    y = HttpResponse(govde, content_type='application/pdf' if pdf else
                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    y['Content-Disposition'] = 'attachment; filename="%s.%s"' % (ad, 'pdf' if pdf else 'xlsx')
    return y


def satis_kategori_gruplari(request):
    """Genel Müdür/Operatör: hangi ham Menulux kategorilerinin tek bir başlık altında gösterileceğini tanımlar."""
    personel, git = _hazir(request, ESLESTIRME_ROLLERI)
    if git:
        return git
    if request.method == 'POST':
        islem = request.POST.get('islem')
        if islem == 'sil':
            KategoriGrubu.objects.filter(id=request.POST.get('id')).delete()
            messages.success(request, 'Grup silindi.')
        else:
            ad = (request.POST.get('ad') or '').strip()
            uyeler = [u.strip() for u in (request.POST.get('uyeler') or '').split('\n') if u.strip()]
            if not ad or not uyeler:
                messages.error(request, 'Grup adı ve en az bir kategori adı girmelisiniz.')
            else:
                gid = request.POST.get('id')
                if gid:
                    KategoriGrubu.objects.filter(id=gid).update(ad=ad, uyeler=uyeler)
                else:
                    KategoriGrubu.objects.create(ad=ad, uyeler=uyeler, sira=KategoriGrubu.objects.count())
                messages.success(request, 'Kategori grubu kaydedildi.')
        return redirect('satis_kategori_gruplari')
    gruplar = list(KategoriGrubu.objects.all())
    ham_kategoriler = []
    if mx.ayarli_mi():
        try:
            ana = mx.ana_id()
            bugun = timezone.localdate()
            ham = mx.coklu([mx.kategori_is(ana, bugun - datetime.timedelta(days=30), bugun, ana)])[0]
            ham_kategoriler = sorted({(r.get('Name') or '').strip() for r in ham if r.get('Name')})
        except Exception:
            ham_kategoriler = []
    return _sr_render(request, 'satis_kategori_gruplari.html', {
        'personel': personel, 'aktif': 'satis', 'gruplar': gruplar, 'ham_kategoriler': ham_kategoriler,
    })
