"""QR Menü Yönetimi ekranları (Geek + Baga).

Yetki: Genel Müdür, Operatör, Yatırımcı — iki markanın menüsünü de görür ve
değiştirir. Diğer roller bu modülü görmez (nav'da yoktur, URL'ye girerse ana
sayfaya döner).

Her kayıt / silme / sıralama sonrası markanın CSV'si üretilip R2'ye yazılır
(bkz. menu_yayin.py). Yayın başarısız olursa kayıt GERİ ALINMAZ; kullanıcıya
açık hata gösterilir ve "Yeniden yayınla" düğmesi sunulur.
"""
import re
import uuid
from urllib.parse import urlencode
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django import forms
from django.contrib import messages
from django.core.files.base import ContentFile
from django.db.models import Count, Max, Q
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models.deletion import ProtectedError

from .menu_sema import ALERJEN_ETIKET, MARKALAR, MENU_YETKILI_ROLLER
from .menu_yayin import csv_adresi, yayinla
from .models import MenuKategori, MenuMarka, MenuUrun
from .views import _aktif_personel, _cikis_mi, _logout


# ------------------------------------------------------------------ yardımcılar
def _giris(request):
    """(personel, hata_yaniti) — yetkisiz ise ikincisi dolu döner."""
    if not request.user.is_authenticated:
        return None, redirect('ana_sayfa')
    if _cikis_mi(request):
        return None, _logout(request)
    personel = _aktif_personel(request)
    if personel is None or personel.rol not in MENU_YETKILI_ROLLER:
        return None, redirect('ana_sayfa')
    return personel, None


_TR = str.maketrans({'ı': 'i', 'İ': 'i', 'ş': 's', 'Ş': 's', 'ğ': 'g', 'Ğ': 'g',
                     'ü': 'u', 'Ü': 'u', 'ö': 'o', 'Ö': 'o', 'ç': 'c', 'Ç': 'c'})


def tr_slug(metin):
    s = str(metin or '').translate(_TR).lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:80]


def _fiyat_oku(ham):
    s = str(ham or '').replace('₺', '').replace('TL', '').replace('tl', '').replace(' ', '').strip()
    if not s:
        raise ValueError('Fiyat boş olamaz.')
    if ',' in s and '.' in s:           # 1.250,50 -> 1250.50
        s = s.replace('.', '').replace(',', '.')
    else:
        s = s.replace(',', '.')
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise ValueError('Geçerli bir fiyat girin.')
    if d < 0 or d >= 100000:
        raise ValueError('Fiyat 0 ile 99.999 arasında olmalı.')
    return d.quantize(Decimal('0.01'))


def _marka_al(marka_kod):
    if marka_kod not in MARKALAR:
        from django.http import Http404
        raise Http404()
    return get_object_or_404(MenuMarka, kod=marka_kod)


def _yayinla_ve_bildir(request, marka, basari_metni):
    ok, hata = yayinla(marka)
    if ok:
        messages.success(request, basari_metni + ' QR menüsü güncellendi (en geç 1 dakikada sitede görünür).')
    else:
        messages.error(request, 'Kayıt yapıldı ancak QR menüsüne YAYINLANAMADI: %s — '
                                'Aşağıdaki "Yeniden yayınla" düğmesiyle tekrar deneyin.' % hata)
    return ok


def _sirayi_normalle(nesneler):
    for i, o in enumerate(nesneler, 1):
        if o.sira != i * 10:
            o.sira = i * 10
            o.save(update_fields=['sira'])


def _komsuyla_degistir(kardesler, hedef_id, yon):
    """Kardeşler zaten sıralı bir liste. hedef'i yukarı/aşağı bir adım taşır."""
    kardesler = list(kardesler)
    _sirayi_normalle(kardesler)
    idx = next((i for i, o in enumerate(kardesler) if o.id == hedef_id), None)
    if idx is None:
        return False
    j = idx - 1 if yon == 'yukari' else idx + 1
    if j < 0 or j >= len(kardesler):
        return False
    a, b = kardesler[idx], kardesler[j]
    a.sira, b.sira = b.sira, a.sira
    a.save(update_fields=['sira'])
    b.save(update_fields=['sira'])
    return True


def _ctx(request, personel, marka, **extra):
    d = {'personel': personel, 'aktif': 'menu_yonetim', 'marka': marka,
         'sema': MARKALAR[marka.kod] if marka else None,
         'markalar': list(MenuMarka.objects.all())}
    d.update(extra)
    return d


# ------------------------------------------------------------------ marka seçimi
def menu_yonetim(request):
    personel, yanit = _giris(request)
    if yanit:
        return yanit
    kartlar = []
    for m in MenuMarka.objects.all():
        sayilar = m.urunler.aggregate(toplam=Count('id'))
        aktif = m.urunler.filter(aktif=True).count()
        kartlar.append({'marka': m, 'toplam': sayilar['toplam'], 'aktif': aktif,
                        'kategori': m.kategoriler.count(), 'csv': csv_adresi(m.kod)})
    return render(request, 'menu_yonetim.html', {'personel': personel, 'aktif': 'menu_yonetim',
                                                 'kartlar': kartlar})


def menu_yayinla_view(request, marka_kod):
    """Elle 'Yeniden yayınla' (POST)."""
    personel, yanit = _giris(request)
    if yanit:
        return yanit
    marka = _marka_al(marka_kod)
    if request.method == 'POST':
        ok, hata = yayinla(marka)
        if ok:
            messages.success(request, '%s menüsü QR sitesine yayınlandı.' % marka.ad)
        else:
            messages.error(request, 'Yayınlanamadı: %s' % hata)
    sonraki = request.POST.get('sonraki') or ''
    if sonraki.startswith('/') and not sonraki.startswith('//'):
        return redirect(sonraki)
    return redirect('menu_urunler', marka_kod=marka.kod)


# ------------------------------------------------------------------ ürün listesi
def menu_urunler(request, marka_kod):
    personel, yanit = _giris(request)
    if yanit:
        return yanit
    marka = _marka_al(marka_kod)

    if request.method == 'POST':
        islem = request.POST.get('islem')
        sorgu = urlencode({k: request.POST.get(k) for k in ('q', 'kat', 'pasif') if request.POST.get(k)})
        url = request.path + ('?' + sorgu if sorgu else '')

        if islem == 'toplu_kaydet':
            idler = [int(x) for x in request.POST.getlist('id') if x.isdigit()]
            urunler = {u.id: u for u in MenuUrun.objects.filter(marka=marka, id__in=idler)}
            degisen, hatalar = 0, []
            for uid in idler:
                u = urunler.get(uid)
                if not u:
                    continue
                try:
                    yeni_fiyat = _fiyat_oku(request.POST.get('fiyat_%d' % uid))
                except ValueError as e:
                    hatalar.append('%s: %s' % (u.urun_adi, e))
                    continue
                yeni_aktif = ('aktif_%d' % uid) in request.POST
                if yeni_fiyat != u.fiyat or yeni_aktif != u.aktif:
                    u.fiyat, u.aktif = yeni_fiyat, yeni_aktif
                    u.save(update_fields=['fiyat', 'aktif', 'guncelleme'])
                    degisen += 1
            for h in hatalar:
                messages.error(request, h)
            if degisen:
                _yayinla_ve_bildir(request, marka, '%d ürün güncellendi.' % degisen)
            elif not hatalar:
                messages.success(request, 'Değişiklik yok.')
            return redirect(url)

        if islem == 'sirala':
            try:
                uid = int(request.POST.get('urun_id'))
            except (TypeError, ValueError):
                return redirect(url)
            u = MenuUrun.objects.filter(marka=marka, id=uid).first()
            if u and _komsuyla_degistir(MenuUrun.objects.filter(marka=marka, kategori=u.kategori).order_by('sira', 'id'),
                                        u.id, request.POST.get('yon')):
                _yayinla_ve_bildir(request, marka, 'Sıralama değişti.')
            return redirect(url)

        return redirect(url)

    q = (request.GET.get('q') or '').strip()
    kat_id = request.GET.get('kat') or ''
    pasif_goster = request.GET.get('pasif') == '1'
    qs = MenuUrun.objects.filter(marka=marka).select_related('kategori').order_by('kategori__sira', 'kategori__id', 'sira', 'id')
    if q:
        qs = qs.filter(Q(urun_adi__icontains=q) | Q(urun_adi_en__icontains=q) | Q(kod__icontains=q))
    if kat_id.isdigit():
        qs = qs.filter(kategori_id=int(kat_id))
    if not pasif_goster:
        qs = qs.filter(aktif=True)
    urunler = list(qs)
    gorunen_sayisi = len(urunler)
    siralama_acik = bool(kat_id.isdigit() and not q)   # sıra okları yalnızca tek kategoride
    for u in urunler:
        u.kucuk_gorsel = u.gorsel_url()
    pasif_sayisi = MenuUrun.objects.filter(marka=marka, aktif=False).count()
    return render(request, 'menu_urunler.html', _ctx(
        request, personel, marka, urunler=urunler, q=q, kat_id=kat_id, pasif_goster=pasif_goster,
        pasif_sayisi=pasif_sayisi, siralama_acik=siralama_acik, gorunen=gorunen_sayisi,
        kategoriler=list(marka.kategoriler.all()), csv=csv_adresi(marka.kod)))


# ------------------------------------------------------------------ ürün formu
MAX_GORSEL_KENAR = 1200


def _gorsel_hazirla(dosya, marka_kod, urun_kod):
    """Yüklenen fotoğrafı (istemci küçültemediyse) en uzun kenarı 1200px olacak şekilde
    küçültüp JPEG/PNG olarak döndürür. İstemci zaten küçülttüyse dokunmaz."""
    from PIL import Image, ImageOps
    dosya.seek(0)
    img = Image.open(dosya)
    img = ImageOps.exif_transpose(img)
    alfa = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
    if max(img.size) > MAX_GORSEL_KENAR:
        img.thumbnail((MAX_GORSEL_KENAR, MAX_GORSEL_KENAR), Image.LANCZOS)
    cikis = BytesIO()
    if alfa:
        img.convert('RGBA').save(cikis, 'PNG', optimize=True)
        uzanti = 'png'
    else:
        img.convert('RGB').save(cikis, 'JPEG', quality=85, optimize=True)
        uzanti = 'jpg'
    ad = '%s-%s-%s.%s' % (marka_kod, urun_kod, uuid.uuid4().hex[:8], uzanti)
    return ad, ContentFile(cikis.getvalue())


def _gorsel_dogrula(alan):
    """Yüklenen görsel gerçekten depoda mı ve herkese açık adresten okunuyor mu? (ok, açıklama).
    Yerel diskte (geliştirme) adres http değilse yalnızca dosyanın varlığına bakılır."""
    try:
        if not alan or not alan.name:
            return False, 'Görsel kaydı oluşmadı.'
        if not alan.storage.exists(alan.name):
            return False, 'Dosya depoya yazılamadı.'
        url = alan.url
        if url.startswith('http'):
            import urllib.request
            istek = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'GeekPanel-kontrol'})
            with urllib.request.urlopen(istek, timeout=6) as r:
                if r.status >= 400:
                    return False, 'Adres %s döndürdü (%s).' % (r.status, url)
    except Exception as e:
        return False, ('%s: %s' % (e.__class__.__name__, e))[:220]
    return True, ''


def _eski_dosyayi_sil(alan):
    try:
        if alan and alan.name:
            alan.storage.delete(alan.name)
    except Exception:
        pass   # eski dosya silinemezse kayıt akışını bozma


class MenuUrunForm(forms.ModelForm):
    kod = forms.CharField(required=False, max_length=80, label='Ürün kodu')
    fiyat = forms.CharField(label='Fiyat (₺)')
    protein = forms.CharField(required=False, label='Protein (g)')
    foto = forms.ImageField(required=False, label='Fotoğraf')
    foto_kaldir = forms.BooleanField(required=False, label='Fotoğrafı kaldır')

    class Meta:
        model = MenuUrun
        fields = ['kategori', 'urun_adi', 'urun_adi_en', 'aciklama', 'aciklama_en', 'icerik', 'icerik_en',
                  'kalori', 'protein', 'sut', 'yumurta', 'gluten', 'sert_kabuklu_yemis', 'yer_fistigi', 'susam',
                  'soya', 'hardal', 'sirke_tursu', 'balik', 'koruyucu_madde', 'vegan',
                  'sube_notu', 'sube_notu_en', 'gorsel_harici', 'aktif', 'fiyat']

    def __init__(self, *args, marka=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.marka = marka
        sema = MARKALAR[marka.kod]
        self.fields['kategori'].queryset = MenuKategori.objects.filter(marka=marka)
        self.fields['kategori'].empty_label = 'Kategori seçin'
        for f in self.fields.values():
            w = f.widget
            if isinstance(w, (forms.CheckboxInput, forms.FileInput)):
                continue
            w.attrs['class'] = 'input'
            if isinstance(w, forms.Textarea):
                w.attrs['rows'] = 3
        self.fields['fiyat'].widget.attrs.update({'inputmode': 'decimal', 'autocomplete': 'off'})
        self.fields['protein'].widget.attrs.update({'inputmode': 'decimal', 'autocomplete': 'off'})
        self.fields['foto'].widget.attrs.update({'accept': 'image/*', 'id': 'mn-foto'})
        # Markada olmayan alanları formdan çıkar (Baga: 4 alerjen, içerik alanları; Geek: içerik yok)
        for a in list(ALERJEN_ETIKET):
            if a not in sema['alerjenler']:
                self.fields.pop(a, None)
        if not sema['icerik']:
            self.fields.pop('icerik', None)
            self.fields.pop('icerik_en', None)
        if self.instance and self.instance.pk:
            self.fields.pop('kod', None)
            if self.instance.fiyat is not None:
                self.initial['fiyat'] = format(self.instance.fiyat.normalize(), 'f').replace('.', ',')
            if self.instance.protein is not None:
                self.initial['protein'] = format(self.instance.protein.normalize(), 'f').replace('.', ',')

    def clean_fiyat(self):
        try:
            return _fiyat_oku(self.cleaned_data.get('fiyat'))
        except ValueError as e:
            raise forms.ValidationError(str(e))

    def clean_protein(self):
        ham = (self.cleaned_data.get('protein') or '').replace(',', '.').strip()
        if not ham:
            return None
        try:
            d = Decimal(ham)
        except InvalidOperation:
            raise forms.ValidationError('Geçerli bir sayı girin.')
        if d < 0 or d > 999:
            raise forms.ValidationError('0 ile 999 arasında olmalı.')
        return d.quantize(Decimal('0.1'))

    def clean(self):
        c = super().clean()
        if 'kod' in self.fields:                      # yalnızca yeni ürün
            kod = tr_slug(c.get('kod') or '') or tr_slug(c.get('urun_adi') or '')
            if not kod:
                self.add_error('kod', 'Ürün kodu oluşturulamadı; ürün adını girin.')
            elif MenuUrun.objects.filter(marka=self.marka, kod=kod).exists():
                self.add_error('kod', 'Bu kod bu markada zaten kullanılıyor: %s' % kod)
            else:
                c['kod'] = kod
        return c


def menu_urun_form(request, marka_kod, urun_id=None):
    personel, yanit = _giris(request)
    if yanit:
        return yanit
    marka = _marka_al(marka_kod)
    sema = MARKALAR[marka.kod]
    urun = get_object_or_404(MenuUrun, id=urun_id, marka=marka) if urun_id else None
    geri = request.GET.get('kat') or ''

    if request.method == 'POST' and urun and request.POST.get('islem') == 'sil':
        ad = urun.urun_adi
        _eski_dosyayi_sil(urun.gorsel)
        urun.delete()
        _yayinla_ve_bildir(request, marka, '"%s" silindi.' % ad)
        return redirect('menu_urunler', marka_kod=marka.kod)

    if request.method == 'POST':
        form = MenuUrunForm(request.POST, request.FILES, instance=urun, marka=marka)
        foto_secildi = request.POST.get('foto_secildi') == '1'
        if foto_secildi and 'foto' not in request.FILES:
            # tarayıcıda fotoğraf seçilmiş ama sunucuya ulaşmamış: sessizce "kaydedildi" deme
            messages.error(request, 'Seçtiğin fotoğraf sunucuya ulaşmadı, ürün KAYDEDİLMEDİ. Fotoğrafı yeniden seçip tekrar dene '
                                    '(dosya çok büyükse ya da bağlantı kesildiyse bu olur).')
            return render(request, 'menu_urun_form.html', _form_ctx(request, personel, marka, sema, urun, form, geri))
        if form.is_valid():
            obj = form.save(commit=False)
            obj.marka = marka
            yeni = urun is None
            if yeni:
                obj.kod = form.cleaned_data['kod']
                son = MenuUrun.objects.filter(marka=marka, kategori=obj.kategori).aggregate(m=Max('sira'))['m'] or 0
                obj.sira = son + 10
            elif form.instance.pk and 'kategori' in form.changed_data:
                son = MenuUrun.objects.filter(marka=marka, kategori=obj.kategori).aggregate(m=Max('sira'))['m'] or 0
                obj.sira = son + 10
            foto = form.cleaned_data.get('foto')
            eski_ad = ''
            try:
                if form.cleaned_data.get('foto_kaldir') and not foto:
                    _eski_dosyayi_sil(obj.gorsel)
                    obj.gorsel = None
                    obj.gorsel_harici = ''
                elif foto:
                    ad, icerik = _gorsel_hazirla(foto, marka.kod, obj.kod)
                    # DİKKAT: obj.gorsel her çağrıda aynı FieldFile nesnesidir; .save() onu yerinde günceller.
                    # Eski dosya ADI önceden metin olarak alınmalı, yoksa yeni yüklenen dosya silinir.
                    eski_ad = (obj.gorsel.name if obj.pk and obj.gorsel else '') or ''
                    obj.gorsel.save(ad, icerik, save=False)
            except Exception as e:
                messages.error(request, 'Fotoğraf yüklenemedi: %s' % e)
                return render(request, 'menu_urun_form.html', _form_ctx(request, personel, marka, sema, urun, form, geri))
            obj.save()
            if foto and eski_ad and eski_ad != obj.gorsel.name:
                try:
                    obj.gorsel.storage.delete(eski_ad)      # yeni kayıt başarılı olduktan sonra eskiyi sil
                except Exception:
                    pass
            foto_notu = ''
            if foto:
                ok, aciklama = _gorsel_dogrula(obj.gorsel)
                if ok:
                    foto_notu = ' Fotoğraf yüklendi.'
                else:
                    messages.warning(request, 'Fotoğraf kaydedildi ama okunabildiği doğrulanamadı: %s — R2 ayarlarını '
                                              '(R2_PUBLIC_URL, bucket erişimi) kontrol et.' % aciklama)
            _yayinla_ve_bildir(request, marka, '"%s" %s.%s' % (obj.urun_adi, 'eklendi' if yeni else 'kaydedildi', foto_notu))
            return redirect('%s?kat=%d' % (reverse('menu_urunler', args=[marka.kod]), obj.kategori_id))
    else:
        baslangic = {}
        if not urun and geri.isdigit():
            baslangic['kategori'] = int(geri)
        form = MenuUrunForm(instance=urun, marka=marka, initial=baslangic)
    return render(request, 'menu_urun_form.html', _form_ctx(request, personel, marka, sema, urun, form, geri))


def _form_ctx(request, personel, marka, sema, urun, form, geri):
    alerjen_alanlari = [(a, ALERJEN_ETIKET[a], form[a]) for a in sema['alerjenler'] if a in form.fields]
    return _ctx(request, personel, marka, urun=urun, form=form, alerjen_alanlari=alerjen_alanlari,
                geri_kat=geri, onizleme=urun.gorsel_url() if urun else '')


# ------------------------------------------------------------------ kategoriler
_KAT_KOD = re.compile(r'^[a-z0-9]{2,40}$')


def menu_kategoriler(request, marka_kod):
    personel, yanit = _giris(request)
    if yanit:
        return yanit
    marka = _marka_al(marka_kod)
    sema = MARKALAR[marka.kod]
    url = request.path

    if request.method == 'POST':
        islem = request.POST.get('islem')
        if islem == 'ekle':
            kod = (request.POST.get('kod') or '').strip().lower()
            ad = (request.POST.get('ad') or '').strip()
            ad_en = (request.POST.get('ad_en') or '').strip()
            if not _KAT_KOD.match(kod):
                messages.error(request, 'Kategori kodu yalnızca küçük harf ve rakamdan oluşmalı (ör. "pizzalar"), 2-40 karakter. '
                                        'Kod sonradan değiştirilemez.')
            elif not ad:
                messages.error(request, 'Kategori adı (TR) boş olamaz.')
            elif MenuKategori.objects.filter(marka=marka, kod=kod).exists():
                messages.error(request, 'Bu kod zaten var: %s' % kod)
            else:
                son = marka.kategoriler.aggregate(m=Max('sira'))['m'] or 0
                MenuKategori.objects.create(marka=marka, kod=kod, ad=ad, ad_en=ad_en, sira=son + 10)
                if kod not in sema['sitede_kodlar']:
                    messages.error(request, 'Kategori eklendi AMA "%s" kodu %s QR sitesinde tanımlı değil — '
                                            'sitenin kodunda (CATEGORIES) bu kod eklenmedikçe bu kategorideki ürünler '
                                            'sitede görünmez.' % (kod, marka.ad))
                _yayinla_ve_bildir(request, marka, 'Kategori eklendi.')
            return redirect(url)
        try:
            kid = int(request.POST.get('kat_id'))
        except (TypeError, ValueError):
            return redirect(url)
        kat = MenuKategori.objects.filter(marka=marka, id=kid).first()
        if not kat:
            return redirect(url)
        if islem == 'kaydet':
            ad = (request.POST.get('ad') or '').strip()
            if not ad:
                messages.error(request, 'Kategori adı (TR) boş olamaz.')
            else:
                kat.ad = ad
                kat.ad_en = (request.POST.get('ad_en') or '').strip()
                kat.save(update_fields=['ad', 'ad_en'])
                _yayinla_ve_bildir(request, marka, 'Kategori kaydedildi.')
        elif islem == 'sirala':
            if _komsuyla_degistir(marka.kategoriler.order_by('sira', 'id'), kat.id, request.POST.get('yon')):
                _yayinla_ve_bildir(request, marka, 'Sıralama değişti.')
        elif islem == 'sil':
            try:
                kat.delete()
                _yayinla_ve_bildir(request, marka, 'Kategori silindi.')
            except ProtectedError:
                messages.error(request, 'Bu kategoride ürün var; önce ürünleri başka kategoriye taşıyın veya silin.')
        return redirect(url)

    kategoriler = list(marka.kategoriler.annotate(urun_sayisi=Count('urunler')))
    for k in kategoriler:
        k.sitede_tanimli = k.kod in sema['sitede_kodlar']
    return render(request, 'menu_kategoriler.html', _ctx(request, personel, marka, kategoriler=kategoriler))
