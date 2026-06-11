from django.contrib import admin
from .models import Sube, Personel, Vardiya, Mola, Puantaj, KodKilit, Zayi, Kalibrasyon


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
