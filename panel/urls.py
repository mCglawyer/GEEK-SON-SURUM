from django.urls import path
from . import views

urlpatterns = [
    path('manifest.webmanifest', views.pwa_manifest, name='pwa_manifest'),
    path('sw.js', views.pwa_service_worker, name='pwa_sw'),
    path('icons/<str:ad>', views.pwa_icon, name='pwa_icon'),
    path('', views.ana_sayfa, name='ana_sayfa'),
    path('puantaj/', views.puantaj_sayfa, name='puantaj'),
    path('mola/', views.mola_sayfa, name='mola'),
    path('ekip/', views.ekip_sayfa, name='ekip'),
    path('puantaj/excel/', views.puantaj_excel_export, name='puantaj_excel_export'),
    path('zayi/', views.zayi_sayfa, name='zayi'),
    path('zayi/excel/', views.zayi_excel_export, name='zayi_excel_export'),
    path('sevkiyat/', views.sevkiyat_sayfa, name='sevkiyat'),
    path('sevkiyat/<int:talep_id>/belge/<str:tip>/', views.sevkiyat_belge, name='sevkiyat_belge'),
    path('sevkiyat/<int:talep_id>/excel/', views.sevkiyat_excel, name='sevkiyat_excel'),
    path('kalibrasyon/', views.kalibrasyon_sayfa, name='kalibrasyon'),
    path('irsaliye/', views.irsaliye_sayfa, name='irsaliye'),
    path('stok/', views.stok_sayimi, name='stok'),
    path('stok/excel/', views.stok_excel, name='stok_excel'),
    path('kvkk/', views.kvkk, name='kvkk'),
    path('kullanim-kosullari/', views.kullanim_kosullari, name='kullanim_kosullari'),
    path('gizlilik/', views.gizlilik, name='gizlilik'),
]
