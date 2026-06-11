# Personel Takip Sistemi (Temiz Kurulum)

Bu, mevcut sistemin temiz mimariyle yeniden kurulan sürümüdür.
Şu an sadece çalışan bir iskelet içerir; modeller, panel ve raporlama
sonraki adımlarda eklenecektir.

## İlk kurulum adımları (yerel - Visual Studio)

Aşağıdaki komutları proje klasörünün içindeyken, Visual Studio'nun
terminalinde sırayla çalıştırın.

1. Sanal ortam oluştur ve aktif et:
       python -m venv venv
       venv\Scripts\activate        (Windows)

2. Gerekli paketleri kur:
       pip install -r requirements.txt

3. Bir SECRET_KEY üret:
       python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

4. `.env.example` dosyasını kopyalayıp `.env` olarak kaydet ve
   DJANGO_SECRET_KEY satırına 3. adımda üretilen anahtarı yapıştır.

5. Veritabanını oluştur:
       python manage.py migrate

6. Yönetici (admin) hesabı oluştur:
       python manage.py createsuperuser

7. Sunucuyu başlat:
       python manage.py runserver

Tarayıcıda http://127.0.0.1:8000 açıldığında "Kurulum başarılı"
yazısını görmelisin.
