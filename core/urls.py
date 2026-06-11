"""core projesi URL yapılandırması."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('panel.urls')),
]

# Geliştirme ortamında yüklenen medya dosyalarını (kalibrasyon fotoğrafları) sun
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
