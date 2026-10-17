from django.contrib import admin
from .models import (Sube, Personel, Vardiya, Puantaj, KodKilit, Kalibrasyon, Irsaliye, StokUrun, StokSayim, StokSayimKalem, SevkiyatTalep, SevkiyatKalem, Urun, SiparisHareket, KahveSoru, GunlukSoru, SoruAyar,
                     MolaOturum, SubeMolaToken, MesaiKayit, SubeMesaiToken,
                     MutfakZayi, MutfakZayiKalemi, MutfakMaliyetKalemi, MutfakTarif, MutfakTarifKalemi,
                     EgitimDokuman, EgitimSoru, EgitimDurum, EgitimAyar, EgitimAcikCevap,
                     DenetimBolum, DenetimMadde, Denetim, DenetimCevap,
                     GSosyalGonderi, GSosyalGorsel, IlginHaber, GeriBildirim,
                     SubeDegerlendirmeToken, MusteriDegerlendirme,
                     MenuMarka, MenuKategori, MenuUrun)

@admin.register(Sube)
class SubeAdmin(admin.ModelAdmin):
    list_display = ('ad', 'depo_mu', 'mutfak_var', 'google_yorum_url')
    list_filter = ('depo_mu', 'mutfak_var')
    search_fields = ('ad',)

@admin.action(description="Seçili personelin giriş kodunu yenile")
def kodu_yenile(modeladmin, request, queryset):
    for p in queryset:
        p.kodu_yenile()

@admin.register(Personel)
class PersonelAdmin(admin.ModelAdmin):
    list_display = ('ad_soyad', 'sube', 'rol', 'egitmen', 'geri_bildirim_yetkilisi', 'giris_kodu', 'user')
    list_filter = ('rol', 'sube', 'egitmen', 'geri_bildirim_yetkilisi')
    list_editable = ('egitmen', 'geri_bildirim_yetkilisi')
    search_fields = ('ad_soyad', 'giris_kodu')
    autocomplete_fields = ('user', 'sube')
    filter_horizontal = ('sorumlu_subeler',)
    readonly_fields = ('giris_kodu',)
    actions = [kodu_yenile]

@admin.register(Vardiya)
class VardiyaAdmin(admin.ModelAdmin):
    list_display = ('personel', 'tarih', 'vardiya_tipi', 'durum')
    list_filter = ('durum', 'vardiya_tipi', 'tarih')
    search_fields = ('personel__ad_soyad',)
    date_hierarchy = 'tarih'

@admin.register(MolaOturum)
class MolaOturumAdmin(admin.ModelAdmin):
    """Şube QR ile (ya da yetkili biri tarafından manuel) başlatılan/bitirilen mola giriş-çıkış kayıtları."""
    list_display = ('personel', 'sube', 'baslangic', 'bitis', 'sure_dk', 'kullanilan_dk', 'uyarildi', 'manuel_mi')
    list_filter = ('sube', 'uyarildi', 'manuel_mi', 'baslangic')
    search_fields = ('personel__ad_soyad',)
    date_hierarchy = 'baslangic'
    autocomplete_fields = ('personel', 'sube', 'manuel_giren')

@admin.register(SubeMolaToken)
class SubeMolaTokenAdmin(admin.ModelAdmin):
    list_display = ('sube', 'token', 'olusturma')
    search_fields = ('sube__ad', 'token')
    readonly_fields = ('olusturma',)

@admin.register(MesaiKayit)
class MesaiKayitAdmin(admin.ModelAdmin):
    """Şube QR ile (ya da yetkili biri tarafından manuel) başlatılan/bitirilen mesai giriş-çıkış kayıtları."""
    list_display = ('sube', 'personel', 'personel_ad_arsiv', 'giris', 'cikis', 'manuel_mi')
    list_filter = ('sube', 'manuel_mi', 'giris')
    search_fields = ('personel__ad_soyad', 'personel_ad_arsiv')
    date_hierarchy = 'giris'
    autocomplete_fields = ('personel', 'sube', 'manuel_giren')

@admin.register(SubeMesaiToken)
class SubeMesaiTokenAdmin(admin.ModelAdmin):
    list_display = ('sube', 'token')
    search_fields = ('sube__ad', 'token')

@admin.register(Puantaj)
class PuantajAdmin(admin.ModelAdmin):
    list_display = ('personel', 'ay', 'calisilan_gun', 'eksik_gun',
                    'izinli_gun', 'raporlu_gun', 'manuel_duzenlendi')
    list_filter = ('ay', 'manuel_duzenlendi')
    search_fields = ('personel__ad_soyad',)

@admin.register(KodKilit)
class KodKilitAdmin(admin.ModelAdmin):
    list_display = ('ip', 'hatali_deneme', 'kilit_bitis')
    readonly_fields = ('ip', 'hatali_deneme', 'kilit_bitis')

@admin.register(Kalibrasyon)
class KalibrasyonAdmin(admin.ModelAdmin):
    list_display = ('sube', 'giren_ad', 'olusturma')
    list_filter = ('sube', 'olusturma')
    search_fields = ('giren_ad',)
    readonly_fields = ('olusturma',)

@admin.register(Irsaliye)
class IrsaliyeAdmin(admin.ModelAdmin):
    list_display = ('giren_ad', 'aciklama', 'olusturma')
    list_filter = ('olusturma',)
    search_fields = ('giren_ad', 'aciklama')
    readonly_fields = ('olusturma',)

@admin.register(StokUrun)
class StokUrunAdmin(admin.ModelAdmin):
    list_display = ('sira', 'ad', 'kategori', 'kapali_icerik', 'acik_carpan', 'aktif')
    list_filter = ('kategori', 'aktif')
    search_fields = ('ad', 'kategori')
    list_editable = ('aktif',)
    ordering = ('sira', 'ad')

class StokSayimKalemInline(admin.TabularInline):
    model = StokSayimKalem
    extra = 0

@admin.register(StokSayim)
class StokSayimAdmin(admin.ModelAdmin):
    list_display = ('sube', 'ay', 'giren_ad', 'guncelleme')
    list_filter = ('sube', 'ay')
    search_fields = ('giren_ad',)
    readonly_fields = ('olusturma', 'guncelleme')
    inlines = [StokSayimKalemInline]

class SevkiyatKalemInline(admin.TabularInline):
    model = SevkiyatKalem
    extra = 0

@admin.register(SevkiyatTalep)
class SevkiyatTalepAdmin(admin.ModelAdmin):
    list_display = ('id', 'sube', 'olusturan_ad', 'durum', 'olusturma', 'onay_tarih')
    list_filter = ('durum', 'sube', 'olusturma')
    search_fields = ('olusturan_ad', 'satin_alan_ad', 'sevkiyatci_ad')
    readonly_fields = ('olusturma',)
    inlines = [SevkiyatKalemInline]

@admin.register(Urun)
class UrunAdmin(admin.ModelAdmin):
    list_display = ('ad', 'form', 'kategori', 'koli_icerigi', 'birim', 'aktif')
    list_filter = ('form', 'kategori', 'aktif', 'birim')
    search_fields = ('ad',)
    list_editable = ('aktif',)

@admin.register(SiparisHareket)
class SiparisHareketAdmin(admin.ModelAdmin):
    list_display = ('talep', 'mesaj', 'yapan_ad', 'olusturma')
    list_filter = ('olusturma',)

@admin.register(KahveSoru)
class KahveSoruAdmin(admin.ModelAdmin):
    list_display = ('id', 'kategori', 'metin', 'dogru', 'aktif')
    list_filter = ('kategori', 'aktif')
    search_fields = ('metin',)
    list_editable = ('aktif',)

@admin.register(GunlukSoru)
class GunlukSoruAdmin(admin.ModelAdmin):
    list_display = ('tarih', 'personel', 'sube_ad', 'secilen', 'dogru_mu', 'sure_doldu', 'cevaplandi')
    list_filter = ('tarih', 'dogru_mu', 'sure_doldu', 'cevaplandi')
    search_fields = ('personel__ad_soyad',)

@admin.register(SoruAyar)
class SoruAyarAdmin(admin.ModelAdmin):
    list_display = ('aktif', 'guncelleme')

@admin.register(MutfakZayi)
class MutfakZayiAdmin(admin.ModelAdmin):
    list_display = ('sube', 'personel', 'personel_ad_arsiv', 'olusturma')
    list_filter = ('sube', 'olusturma')
    search_fields = ('personel__ad_soyad', 'personel_ad_arsiv', 'aciklama')
    readonly_fields = ('olusturma',)
    date_hierarchy = 'olusturma'
    autocomplete_fields = ('personel', 'sube')

@admin.register(MutfakZayiKalemi)
class MutfakZayiKalemiAdmin(admin.ModelAdmin):
    list_display = ('tarih', 'sube', 'urun', 'miktar', 'birim', 'personel_ad_arsiv')
    list_filter = ('sube', 'birim', 'tarih')
    search_fields = ('urun', 'personel_ad_arsiv', 'aciklama')
    readonly_fields = ('olusturma', 'urun_anahtar', 'olcu', 'taban_miktar')
    date_hierarchy = 'tarih'
    autocomplete_fields = ('personel', 'sube')

@admin.register(MutfakMaliyetKalemi)
class MutfakMaliyetKalemiAdmin(admin.ModelAdmin):
    list_display = ('ad', 'birim', 'fiyat', 'guncelleme')
    list_filter = ('birim',)
    search_fields = ('ad',)

class MutfakTarifKalemiInline(admin.TabularInline):
    model = MutfakTarifKalemi
    extra = 0
    autocomplete_fields = ('urun',)

@admin.register(MutfakTarif)
class MutfakTarifAdmin(admin.ModelAdmin):
    list_display = ('ad', 'olusturan', 'toplam_maliyet', 'guncelleme')
    search_fields = ('ad',)
    inlines = [MutfakTarifKalemiInline]


@admin.register(EgitimDokuman)
class EgitimDokumanAdmin(admin.ModelAdmin):
    list_display = ('baslik', 'kategori', 'sube', 'aktif', 'olusturma')
    list_filter = ('kategori', 'aktif', 'sube')
    search_fields = ('baslik',)

@admin.register(EgitimSoru)
class EgitimSoruAdmin(admin.ModelAdmin):
    list_display = ('metin', 'kategori', 'tur', 'sube', 'aktif', 'olusturma')
    list_filter = ('kategori', 'tur', 'aktif', 'sube')
    search_fields = ('metin',)

@admin.register(EgitimDurum)
class EgitimDurumAdmin(admin.ModelAdmin):
    list_display = ('personel', 'tamamlandi', 'gecti', 'inceleme_bekliyor', 'son_puan', 'deneme', 'tarih')
    list_filter = ('tamamlandi', 'gecti', 'inceleme_bekliyor')
    search_fields = ('personel__ad_soyad',)
    autocomplete_fields = ('personel',)

@admin.register(EgitimAcikCevap)
class EgitimAcikCevapAdmin(admin.ModelAdmin):
    list_display = ('personel', 'soru', 'deneme_no', 'puanlandi', 'dogru_mu', 'puanlayan', 'olusturma')
    list_filter = ('puanlandi', 'dogru_mu')
    search_fields = ('personel__ad_soyad', 'cevap_metni')
    autocomplete_fields = ('personel', 'puanlayan')

@admin.register(EgitimAyar)
class EgitimAyarAdmin(admin.ModelAdmin):
    list_display = ('acik', 'soru_sayisi', 'sure_sn', 'gecme_puan', 'guncelleme')


class DenetimMaddeInline(admin.TabularInline):
    model = DenetimMadde
    extra = 0

@admin.register(DenetimBolum)
class DenetimBolumAdmin(admin.ModelAdmin):
    list_display = ('ad', 'sira', 'aktif', 'olusturma')
    list_filter = ('aktif',)
    search_fields = ('ad',)
    inlines = [DenetimMaddeInline]

@admin.register(DenetimMadde)
class DenetimMaddeAdmin(admin.ModelAdmin):
    list_display = ('metin', 'bolum', 'sira', 'aktif')
    list_filter = ('aktif', 'bolum')
    search_fields = ('metin',)
    autocomplete_fields = ('bolum',)

class DenetimCevapInline(admin.TabularInline):
    model = DenetimCevap
    extra = 0
    autocomplete_fields = ('madde',)

@admin.register(Denetim)
class DenetimAdmin(admin.ModelAdmin):
    list_display = ('sube', 'denetleyen', 'baslangic', 'bitis', 'tamamlandi', 'toplam_puan')
    list_filter = ('tamamlandi', 'sube')
    search_fields = ('sube__ad', 'denetleyen__ad_soyad')
    date_hierarchy = 'baslangic'
    autocomplete_fields = ('sube', 'denetleyen')
    inlines = [DenetimCevapInline]

class GSosyalGorselInline(admin.TabularInline):
    model = GSosyalGorsel
    extra = 0

@admin.register(GSosyalGonderi)
class GSosyalGonderiAdmin(admin.ModelAdmin):
    list_display = ('yazan_ad', 'olusturma')
    search_fields = ('yazan_ad', 'metin')
    date_hierarchy = 'olusturma'
    inlines = [GSosyalGorselInline]

@admin.register(IlginHaber)
class IlginHaberAdmin(admin.ModelAdmin):
    list_display = ('baslik', 'kaynak', 'sektor_ilgili', 'onaylandi', 'olusturma', 'onaylayan')
    list_filter = ('onaylandi', 'sektor_ilgili', 'kaynak')
    search_fields = ('baslik',)
    date_hierarchy = 'olusturma'

@admin.register(GeriBildirim)
class GeriBildirimAdmin(admin.ModelAdmin):
    list_display = ('kategori', 'sube', 'durum', 'olusturma')
    list_filter = ('kategori', 'durum', 'sube')
    date_hierarchy = 'olusturma'

@admin.register(MusteriDegerlendirme)
class MusteriDegerlendirmeAdmin(admin.ModelAdmin):
    list_display = ('sube', 'puan', 'olusturma')
    list_filter = ('sube', 'puan')
    date_hierarchy = 'olusturma'

@admin.register(SubeDegerlendirmeToken)
class SubeDegerlendirmeTokenAdmin(admin.ModelAdmin):
    list_display = ('sube', 'token', 'olusturma')


class _MenuYayinMixin:
    """Admin'den yapılan menü değişiklikleri de QR menüsüne (CSV) yansısın."""

    def _yayinla(self, request, marka):
        from .menu_yayin import yayinla
        ok, hata = yayinla(marka)
        if ok:
            self.message_user(request, "%s menüsü QR sitesine yayınlandı." % marka.ad)
        else:
            self.message_user(request, "Kayıt yapıldı ama QR menüsü yayınlanamadı: %s" % hata, level='ERROR')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self._yayinla(request, obj.marka)

    def delete_model(self, request, obj):
        marka = obj.marka
        super().delete_model(request, obj)
        self._yayinla(request, marka)

    def delete_queryset(self, request, queryset):
        markalar = {o.marka for o in queryset.select_related('marka')}
        super().delete_queryset(request, queryset)
        for m in markalar:
            self._yayinla(request, m)


@admin.register(MenuMarka)
class MenuMarkaAdmin(admin.ModelAdmin):
    list_display = ('ad', 'kod', 'son_yayin', 'son_yayin_hata')
    readonly_fields = ('kod', 'son_yayin', 'son_yayin_hata')


@admin.register(MenuKategori)
class MenuKategoriAdmin(_MenuYayinMixin, admin.ModelAdmin):
    list_display = ('ad', 'marka', 'kod', 'sira')
    list_filter = ('marka',)

    def get_readonly_fields(self, request, obj=None):
        # Kategori kodu QR sitesinde sabittir; oluşturulduktan sonra değişmez.
        return ('kod',) if obj else ()


@admin.register(MenuUrun)
class MenuUrunAdmin(_MenuYayinMixin, admin.ModelAdmin):
    list_display = ('urun_adi', 'marka', 'kategori', 'fiyat', 'aktif')
    list_filter = ('marka', 'kategori', 'aktif')
    search_fields = ('urun_adi', 'urun_adi_en', 'kod')


from .models import TemizlikUrun, TemizlikSayim, TemizlikSayimKalem, TemizlikDuzeltme  # noqa: E402
from .models import TemizlikAyar, TemizlikFiyat  # noqa: E402


@admin.register(TemizlikUrun)
class TemizlikUrunAdmin(admin.ModelAdmin):
    list_display = ('ad', 'birim', 'koli_icerigi', 'urun', 'sira', 'aktif')
    list_editable = ('sira', 'aktif')
    list_filter = ('aktif',)
    search_fields = ('ad',)
    raw_id_fields = ('urun',)


class TemizlikSayimKalemInline(admin.TabularInline):
    model = TemizlikSayimKalem
    extra = 0
    raw_id_fields = ('urun',)


@admin.register(TemizlikSayim)
class TemizlikSayimAdmin(admin.ModelAdmin):
    list_display = ('sube', 'ay', 'tur', 'tarih', 'giren_ad')
    list_filter = ('tur', 'sube')
    inlines = [TemizlikSayimKalemInline]


@admin.register(TemizlikDuzeltme)
class TemizlikDuzeltmeAdmin(admin.ModelAdmin):
    list_display = ('sube', 'ay', 'urun_ad', 'tarih', 'miktar', 'aciklama', 'giren_ad')
    list_filter = ('sube',)


@admin.register(TemizlikAyar)
class TemizlikAyarAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'aktif', 'baslangic', 'guncelleyen', 'son_sifirlama')


@admin.register(TemizlikFiyat)
class TemizlikFiyatAdmin(admin.ModelAdmin):
    list_display = ('urun', 'fiyat', 'birim', 'gecerli', 'giren_ad')
    list_filter = ('birim',)
    search_fields = ('urun__ad',)
    raw_id_fields = ('urun',)


from .models import OyunSkor  # noqa: E402

@admin.register(OyunSkor)
class OyunSkorAdmin(admin.ModelAdmin):
    list_display = ('personel', 'mod', 'skor', 'sure_sn', 'zaman')
    list_filter = ('mod', 'zaman')
    search_fields = ('personel__ad_soyad',)
