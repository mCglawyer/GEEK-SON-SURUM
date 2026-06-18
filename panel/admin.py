from django.contrib import admin
from .models import (Sube, Personel, Vardiya, Mola, Puantaj, KodKilit, Zayi, Kalibrasyon, Irsaliye, StokUrun, StokSayim, StokSayimKalem, SevkiyatTalep, SevkiyatKalem, Urun, SiparisHareket, KahveSoru, GunlukSoru, SoruAyar)


@admin.register(Sube)
class SubeAdmin(admin.ModelAdmin):
    list_display = ('ad', 'depo_mu')
    list_filter = ('depo_mu',)
    search_fields = ('ad',)


@admin.action(description="Seçili personelin giriş kodunu yenile")
def kodu_yenile(modeladmin, request, queryset):
    for p in queryset:
        p.kodu_yenile()


@admin.register(Personel)
class PersonelAdmin(admin.ModelAdmin):
    list_display = ('ad_soyad', 'sube', 'rol', 'giris_kodu', 'user')
    list_filter = ('rol', 'sube')
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


@admin.register(Mola)
class MolaAdmin(admin.ModelAdmin):
    list_display = ('personel', 'tarih', 'mola_tipi', 'baslangic_saati', 'bitis_saati')
    list_filter = ('tarih',)
    search_fields = ('personel__ad_soyad',)


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


@admin.register(Zayi)
class ZayiAdmin(admin.ModelAdmin):
    list_display = ('urun_adi', 'miktar', 'birim', 'sube', 'giren_ad', 'olusturma')
    list_filter = ('sube', 'birim', 'olusturma')
    search_fields = ('urun_adi', 'giren_ad')
    readonly_fields = ('olusturma',)


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
