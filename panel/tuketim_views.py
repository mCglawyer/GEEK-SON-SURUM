"""Bar tüketim & maliyet ekranları: rapor + grafikler, fiyatlar, sayım-sevkiyat eşleme, ayarlar."""
import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib import messages
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from . import tuketim as tk
from . import tuketim_cikti as tc
from .models import Rol, StokSayim, StokUrun, Sube, TuketimAyar, TuketimFiyat, Urun
from .views import _aktif_personel, _cikis_mi, _logout

AYAR_ROLLERI = (Rol.GENEL_MUDUR, Rol.OPERATOR)


def _personel(request):
    if not request.user.is_authenticated:
        return None, redirect('ana_sayfa')
    if _cikis_mi(request):
        return None, _logout(request)
    personel = _aktif_personel(request)
    if personel is None:
        return None, redirect('ana_sayfa')
    return personel, None


def _hazir(request, yonetim=False):
    """(personel, ayar, yanıt). Sistem kapalıyken yalnızca yönetim girer."""
    personel, git = _personel(request)
    if git:
        return None, None, git
    izinli = tk.YONETIM_ROLLERI if yonetim else tk.RAPOR_ROLLERI
    if personel.rol not in izinli:
        return None, None, redirect('ana_sayfa')
    ayar = TuketimAyar.al()
    if not tk.erisebilir(personel, ayar):
        return None, None, render(request, 'tuketim_kapali.html', {'personel': personel, 'aktif': 'tuketim'})
    return personel, ayar, None


def _ortak(personel, ayar, sayfa=''):
    menu = [('Rapor', reverse('tuketim_rapor'), 'rapor')]
    if tk.fiyat_yonetebilir(personel):
        menu += [('Fiyatlar', reverse('tuketim_fiyatlar'), 'fiyatlar'),
                 ('Ürün eşleme', reverse('tuketim_esleme'), 'esleme')]
    if personel.rol in AYAR_ROLLERI:
        menu.append(('Ayarlar', reverse('tuketim_ayar'), 'ayar'))
    return {'tk_menu': [(a, u, k == sayfa) for a, u, k in menu], 'ayar': ayar,
            'sistem_kapali': not ayar.aktif, 'ayar_gorur': personel.rol in AYAR_ROLLERI, 'personel': personel,
            'aktif': 'tuketim'}


def fiyat_oku(metin):
    """'12', '12,5', '1.250,75' -> Decimal (4 hane); boş -> None; bozuk/eksi -> ValueError."""
    t = (metin or '').strip().replace(' ', '')
    if not t:
        return None
    if ',' in t:
        t = t.replace('.', '').replace(',', '.')
    try:
        d = Decimal(t)
    except InvalidOperation:
        raise ValueError(metin)
    if not d.is_finite() or d < 0 or d > Decimal('10000000'):
        raise ValueError(metin)
    return d.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)


def fiyat_yaz(d):
    if d is None:
        return ''
    s = '{:f}'.format(Decimal(d).quantize(Decimal('0.0001')))
    s = s.rstrip('0').rstrip('.') if '.' in s else s
    return s.replace('.', ',')


def _tarih_oku(metin):
    try:
        return datetime.datetime.strptime((metin or '').strip(), '%Y-%m-%d').date()
    except ValueError:
        return None


def tuketim_ana(request):
    personel, ayar, git = _hazir(request)
    return git or redirect('tuketim_rapor')


# ------------------------------------------------------------------ rapor
def _sutunlar(deger_listesi, etiketler):
    """Sütun grafiği için {etiket, deger, yuzde}. Değeri olmayan ay (None) boş çubuk."""
    en_buyuk = max([d for d in deger_listesi if d is not None] or [Decimal('0')])
    cikti = []
    for e, d in zip(etiketler, deger_listesi):
        yuzde = int((d / en_buyuk * 100)) if (d is not None and en_buyuk > 0) else 0
        cikti.append({'etiket': e, 'deger': d, 'yuzde': max(yuzde, 2) if d else 0})
    return cikti


def _varsayilan_ay(subeler):
    """Raporda ay seçilmediyse: kapsamdaki şubelerde sayımı girilmiş en son ay (yoksa bu ay)."""
    son = StokSayim.objects.filter(sube__in=subeler).aggregate(m=Max('ay'))['m'] if subeler else None
    return son or timezone.localdate().replace(day=1)


def _grup(request):
    g = request.GET.get('grup') or ''
    return g if g in ('bar', 'temizlik') else ''


def tuketim_rapor(request):
    personel, ayar, git = _hazir(request)
    if git:
        return git
    subeler = tk.rapor_subeleri(personel)
    ay_ilk = tk.ay_oku(request.GET.get('ay')) if request.GET.get('ay') else _varsayilan_ay(subeler)
    sid = request.GET.get('sube') or ''
    secili = next((s for s in subeler if str(s.id) == sid), None)
    kapsam = [secili] if secili else subeler
    grup = _grup(request)
    veri = tk.hesapla(kapsam, ay_ilk, fiyatli=True, ayar=ayar, grup=grup) if kapsam else None
    onceki, sonraki = tk.ay_komsulari(ay_ilk)

    ctx = _ortak(personel, ayar, 'rapor')
    ctx.update({'subeler': subeler, 'coklu': len(subeler) > 1, 'secili': secili, 'veri': veri, 'ay_deger': ay_ilk.strftime('%Y-%m'),
                'bugun': timezone.localdate(), 'grup': grup, 'gruplar': [('', 'Tümü'), ('bar', 'Bar'), ('temizlik', 'Temizlik')], 'ay_etiket': tk.ay_etiketi(ay_ilk), 'yonetim': tk.fiyat_yonetebilir(personel)})
    q = ('&sube=%s' % secili.id if secili else '') + ('&grup=%s' % grup if grup else '')
    ctx['onceki_url'] = '?ay=%s%s' % (onceki.strftime('%Y-%m'), q)
    ctx['sonraki_url'] = '?ay=%s%s' % (sonraki.strftime('%Y-%m'), q)
    if veri:
        seri = tk.aylik_seri(kapsam, ay_ilk, adet=6, ayar=ayar, grup=grup)
        degerler = seri['seri'][secili.id] if secili else seri['toplam']
        ctx['aylik_sutun'] = _sutunlar(degerler, seri['etiketler'])
        ctx['aylik_var'] = any(d is not None for d in degerler)
        # en çok harcama kalemleri
        kalemler = sorted((r for r in veri['toplam'] if r.get('tutar')), key=lambda r: r['tutar'], reverse=True)[:10]
        en = kalemler[0]['tutar'] if kalemler else Decimal('1')
        ctx['top_kalemler'] = [dict(r, yuzde=max(int(r['tutar'] / en * 100), 2)) for r in kalemler]
        # şubeler arası karşılaştırma (yalnızca birden fazla şube kapsamdaysa)
        sube_tutar = sorted(((c['sube'], c['tutar']) for c in veri['subeler'] if c['tutar'] is not None),
                            key=lambda x: x[1], reverse=True)
        en_s = sube_tutar[0][1] if sube_tutar else Decimal('1')
        ctx['sube_sutun'] = [{'sube': s, 'tutar': t, 'yuzde': max(int(t / en_s * 100), 2) if en_s > 0 else 0} for s, t in sube_tutar]
        if len(veri['subeler']) > 1:                       # ürün × şube maliyet tablosu (en çok harcananlar)
            ilk_30 = sorted((r for r in veri['toplam'] if r.get('tutar')), key=lambda r: r['tutar'], reverse=True)[:30]
            kir = []
            for r in ilk_30:
                hucre = []
                for c in veri['subeler']:
                    x = next((y for y in c['satirlar'] if y['urun'].id == r['urun'].id), None)
                    hucre.append(x['tutar'] if x else None)
                kir.append((r, hucre))
            ctx['kirilim'] = kir
    return render(request, 'tuketim_rapor.html', ctx)


def tuketim_indir(request):
    """Excel / PDF: tur=ay (aylık kullanım+maliyet) | gelen (gün/hafta/ay/özel aralıkta gelen mal ve tutar)."""
    personel, ayar, git = _hazir(request)
    if git:
        return git
    subeler = tk.rapor_subeleri(personel)
    secili = next((s for s in subeler if str(s.id) == (request.GET.get('sube') or '')), None)
    kapsam = [secili] if secili else subeler
    tur = 'gelen' if request.GET.get('tur') == 'gelen' else 'ay'
    pdf = request.GET.get('bicim') == 'pdf'
    if tur == 'ay':
        ay_ilk = tk.ay_oku(request.GET.get('ay')) if request.GET.get('ay') else _varsayilan_ay(subeler)
        veri = tk.hesapla(kapsam, ay_ilk, fiyatli=True, ayar=ayar, grup=_grup(request)) if kapsam else None
        if veri is None:
            return redirect('tuketim_rapor')
        etiket, govde, ad = veri['etiket'], (tc.pdf_bytes if pdf else tc.excel_bytes)('ay', veri['etiket'], secili, veri=veri), \
            'tuketim_%s%s' % (ay_ilk.strftime('%Y_%m'), '_sube%d' % secili.id if secili else '')
    else:
        ref = _tarih_oku(request.GET.get('ref'))
        bas, bit, etiket = tc.aralik_oku(request.GET.get('aralik') or 'ay', ref, _tarih_oku(request.GET.get('bas')),
                                         _tarih_oku(request.GET.get('bit')))
        gelen = tc.gelen_hesapla(kapsam, bas, bit)
        govde = (tc.pdf_bytes if pdf else tc.excel_bytes)('gelen', etiket, secili, gelen=gelen)
        ad = 'gelen_mal_%s_%s%s' % (bas.strftime('%Y%m%d'), bit.strftime('%Y%m%d'), '_sube%d' % secili.id if secili else '')
    y = HttpResponse(govde, content_type='application/pdf' if pdf else
                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    y['Content-Disposition'] = 'attachment; filename="%s.%s"' % (ad, 'pdf' if pdf else 'xlsx')
    return y


# ------------------------------------------------------------------ fiyatlar
def _fiyat_urunleri(hepsi=False, q=''):
    """Fiyat girilecek sevkiyat ürünleri: sayıma ya da temizliğe bağlı olanlar (hepsi=1 ise tüm katalog)."""
    if hepsi:
        qs = Urun.objects.filter(aktif=True)
    else:
        bagli = set(StokUrun.objects.exclude(sevkiyat_urun=None).values_list('sevkiyat_urun_id', flat=True))
        qs = Urun.objects.filter(id__in=bagli)
    if q:
        qs = qs.filter(ad__icontains=q)
    return list(qs.order_by('form', 'kategori', 'ad'))


def _guncel(satirlar, grup, bugun):
    """(fiyat, gecerli) — bugün geçerli olan en son grup fiyatı; yoksa gelecek tarihli ilk fiyat."""
    uygun = [f for f in satirlar if f.sube_id is None and f.grup == grup]
    gecen = [f for f in uygun if f.gecerli <= bugun]
    if gecen:
        f = gecen[-1]
        return f.fiyat, f.gecerli, False
    if uygun:
        f = uygun[0]
        return f.fiyat, f.gecerli, True
    return None, None, False


def tuketim_fiyatlar(request):
    personel, ayar, git = _hazir(request, yonetim=True)
    if git:
        return git
    hepsi = request.GET.get('hepsi') == '1'
    q = (request.GET.get('q') or '').strip()
    bugun = timezone.localdate()
    if request.method == 'POST' and request.POST.get('islem') == 'toplu':
        tarih = _tarih_oku(request.POST.get('tarih')) or bugun
        urunler = _fiyat_urunleri(hepsi=True)
        defter = tk.FiyatDefteri()
        hatalar, yazilan = [], 0
        with transaction.atomic():
            for u in urunler:
                for grup, alan in (('MERKEZ', 'm'), ('FRANCHISE', 'f')):
                    ham = request.POST.get('%s_%d' % (alan, u.id))
                    if ham is None or not ham.strip():
                        continue
                    try:
                        yeni = fiyat_oku(ham)
                    except ValueError:
                        hatalar.append('“%s” için geçersiz fiyat: %s' % (u.ad, ham))
                        continue
                    mevcut_liste = [f for f in defter.satirlar.get(u.id, []) if f.sube_id is None and f.grup == grup]
                    gecen = [f for f in mevcut_liste if f.gecerli <= tarih]
                    if gecen and gecen[-1].fiyat == yeni:
                        continue                                                   # değişmemiş
                    ayni_gun = next((f for f in mevcut_liste if f.gecerli == tarih), None)
                    if ayni_gun:
                        ayni_gun.fiyat = yeni
                        ayni_gun.giren_ad = personel.ad_soyad
                        ayni_gun.save(update_fields=['fiyat', 'giren_ad'])
                    else:
                        TuketimFiyat.objects.create(urun=u, grup=grup, fiyat=yeni, gecerli=tarih, giren_ad=personel.ad_soyad)
                    yazilan += 1
        for h in hatalar:
            messages.error(request, h)
        if yazilan:
            messages.success(request, '%d fiyat kaydedildi (geçerlilik: %s).' % (yazilan, tarih.strftime('%d.%m.%Y')))
        elif not hatalar:
            messages.info(request, 'Değişen bir fiyat yok.')
        sonraki = reverse('tuketim_fiyatlar') + ('?hepsi=1' if hepsi else '')
        return redirect(sonraki)

    defter = tk.FiyatDefteri()
    satirlar = []
    for u in _fiyat_urunleri(hepsi, q):
        sat = defter.satirlar.get(u.id, [])
        m, mt, m_gelecek = _guncel(sat, 'MERKEZ', bugun)
        f, ft, f_gelecek = _guncel(sat, 'FRANCHISE', bugun)
        satirlar.append({'urun': u, 'merkez': m, 'merkez_tarih': mt, 'merkez_gelecek': m_gelecek,
                         'franchise': f, 'franchise_tarih': ft, 'franchise_gelecek': f_gelecek,
                         'istisna': len({x.sube_id for x in sat if x.sube_id})})
    ctx = _ortak(personel, ayar, 'fiyatlar')
    ctx.update({'satirlar': satirlar, 'hepsi': hepsi, 'q': q, 'bugun': bugun.strftime('%Y-%m-%d'),
                'eksik': sum(1 for r in satirlar if r['merkez'] is None or r['franchise'] is None)})
    return render(request, 'tuketim_fiyatlar.html', ctx)


def tuketim_fiyat_detay(request, urun_id):
    personel, ayar, git = _hazir(request, yonetim=True)
    if git:
        return git
    urun = get_object_or_404(Urun, id=urun_id)
    if request.method == 'POST':
        islem = request.POST.get('islem')
        if islem == 'sil':
            f = TuketimFiyat.objects.filter(id=request.POST.get('id'), urun=urun).first()
            if f:
                f.delete()
                messages.success(request, 'Fiyat kaydı silindi.')
        elif islem == 'ekle':
            hedef = request.POST.get('hedef') or ''
            tarih = _tarih_oku(request.POST.get('tarih'))
            try:
                fiyat = fiyat_oku(request.POST.get('fiyat'))
            except ValueError:
                fiyat = None
            sube = None
            grup = ''
            if hedef in ('MERKEZ', 'FRANCHISE'):
                grup = hedef
            elif hedef.startswith('s'):
                sube = Sube.objects.filter(id=hedef[1:] if hedef[1:].isdigit() else 0, depo_mu=False).first()
            if tarih is None or fiyat is None or (not grup and sube is None):
                messages.error(request, 'Hedef, tarih ve geçerli bir fiyat gir.')
            else:
                mevcut = TuketimFiyat.objects.filter(urun=urun, grup=grup, sube=sube, gecerli=tarih).first()
                if mevcut:
                    mevcut.fiyat = fiyat
                    mevcut.giren_ad = personel.ad_soyad
                    mevcut.save(update_fields=['fiyat', 'giren_ad'])
                else:
                    TuketimFiyat.objects.create(urun=urun, grup=grup, sube=sube, fiyat=fiyat, gecerli=tarih,
                                                giren_ad=personel.ad_soyad)
                messages.success(request, 'Fiyat kaydedildi.')
        return redirect('tuketim_fiyat_detay', urun_id=urun.id)
    ctx = _ortak(personel, ayar, 'fiyatlar')
    ctx.update({'urun': urun, 'gecmis': list(urun.tuketim_fiyatlari.select_related('sube').order_by('-gecerli', 'grup', 'sube')),
                'subeler': list(Sube.objects.filter(depo_mu=False).order_by('ad')), 'bugun': timezone.localdate().strftime('%Y-%m-%d')})
    return render(request, 'tuketim_fiyat_detay.html', ctx)


# ------------------------------------------------------------------ eşleme
def tuketim_esleme(request):
    personel, ayar, git = _hazir(request, yonetim=True)
    if git:
        return git
    sevk = list(Urun.objects.filter(aktif=True).order_by('form', 'kategori', 'ad'))
    sevk_id = {u.id: u for u in sevk}
    stoklar = list(StokUrun.objects.select_related('sevkiyat_urun').order_by('sira', 'ad'))
    if request.method == 'POST':
        islem = request.POST.get('islem')
        if islem == 'kaydet':
            degisen = 0
            hatalar = []
            for su in stoklar:
                ham_u = request.POST.get('u_%d' % su.id, '')
                yeni_u = sevk_id.get(int(ham_u)) if ham_u.isdigit() else None
                try:
                    yeni_c = fiyat_oku(request.POST.get('c_%d' % su.id))
                except ValueError:
                    hatalar.append('“%s” için geçersiz çarpan.' % su.ad)
                    continue
                if yeni_c is not None and yeni_c <= 0:
                    hatalar.append('“%s” için çarpan 0’dan büyük olmalı.' % su.ad)
                    continue
                if (su.sevkiyat_urun_id or None) != (yeni_u.id if yeni_u else None) or su.sevkiyat_carpan != yeni_c:
                    su.sevkiyat_urun = yeni_u
                    su.sevkiyat_carpan = yeni_c if yeni_u else None
                    su.save(update_fields=['sevkiyat_urun', 'sevkiyat_carpan'])
                    degisen += 1
            for h in hatalar:
                messages.error(request, h)
            if degisen:
                messages.success(request, '%d ürünün eşlemesi güncellendi.' % degisen)
        elif islem == 'oner_uygula':
            oneri = tk.esleme_oner([s for s in stoklar if not s.sevkiyat_urun_id], sevk)
            for su in stoklar:
                if su.id in oneri:
                    su.sevkiyat_urun = oneri[su.id][0]
                    su.save(update_fields=['sevkiyat_urun'])
            messages.success(request, '%d ürün için öneri uygulandı. Çarpanları kontrol edip gerekirse düzeltin.' % len(oneri))
        elif islem == 'temizlik_ekle':
            mevcut = {st.sevkiyat_urun_id for st in stoklar if st.sevkiyat_urun_id}
            sira = (StokUrun.objects.aggregate(m=Max('sira'))['m'] or 0)
            eklenen = 0
            for u in Urun.objects.filter(aktif=True, form='TEMIZLIK').order_by('kategori', 'ad'):
                if u.id in mevcut:
                    continue
                sira += 1
                StokUrun.objects.create(kategori=tk.TEMIZLIK_GRUBU, ad=u.ad[:200], kapali_icerik=1, acik_carpan=1,
                                        sevkiyat_urun=u, sevkiyat_carpan=1, sira=sira)
                eklenen += 1
            messages.success(request, '%d temizlik ürünü stok sayımına eklendi. Şefler bir sonraki sayımda bunları da sayacak.' % eklenen
                             if eklenen else 'Eklenecek yeni temizlik ürünü yok; hepsi zaten sayımda.')
        return redirect('tuketim_esleme')
    oneri = tk.esleme_oner([s for s in stoklar if not s.sevkiyat_urun_id], sevk)
    satirlar = []
    for su in stoklar:
        o = oneri.get(su.id)
        satirlar.append({'stok': su, 'oneri': o[0] if o else None, 'guven': int(o[1] * 100) if o else None,
                         'varsayilan': tk.varsayilan_carpan(su, su.sevkiyat_urun or (o[0] if o else None))})
    ctx = _ortak(personel, ayar, 'esleme')
    ctx.update({'satirlar': satirlar, 'sevk': sevk, 'bagli': sum(1 for s in stoklar if s.sevkiyat_urun_id),
                'toplam': len(stoklar), 'oneri_sayisi': len(oneri)})
    return render(request, 'tuketim_esleme.html', ctx)


# ------------------------------------------------------------------ ayarlar
def tuketim_ayar(request):
    personel, git = _personel(request)
    if git:
        return git
    if personel.rol not in AYAR_ROLLERI:
        return redirect('ana_sayfa')
    ayar = TuketimAyar.al()
    if request.method == 'POST' and request.POST.get('islem') == 'gruplar':
        gecerli = {k for k, _ in Sube.FIYAT_GRUBU}
        for sb in Sube.objects.filter(depo_mu=False):
            g = request.POST.get('g_%d' % sb.id)
            if g in gecerli and g != sb.fiyat_grubu:
                sb.fiyat_grubu = g
                sb.save(update_fields=['fiyat_grubu'])
        messages.success(request, 'Şube fiyat grupları kaydedildi.')
        return redirect('tuketim_ayar')
    if request.method == 'POST':
        ayar.aktif = request.POST.get('aktif') == 'on'
        ham = (request.POST.get('baslangic') or '').strip()
        try:
            ayar.baslangic = datetime.datetime.strptime(ham, '%Y-%m').date() if ham else None
        except ValueError:
            messages.error(request, 'İlk sayım ayı geçersiz.')
            return redirect('tuketim_ayar')
        ayar.son_gun_ayda = request.POST.get('son_gun_ayda') == 'on'
        ayar.guncelleyen = personel.ad_soyad
        ayar.save()
        messages.success(request, 'Ayarlar kaydedildi.')
        return redirect('tuketim_ayar')
    ctx = _ortak(personel, ayar, 'ayar')
    ctx['baslangic_deger'] = ayar.baslangic.strftime('%Y-%m') if ayar.baslangic else ''
    ctx['sube_gruplari'] = list(Sube.objects.filter(depo_mu=False).order_by('ad'))
    ctx['gruplar'] = Sube.FIYAT_GRUBU
    return render(request, 'tuketim_ayar.html', ctx)
