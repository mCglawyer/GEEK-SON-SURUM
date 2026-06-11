# Geek Panel — Canlıya Alma Rehberi (PythonAnywhere)

Bu rehber sistemi `KULLANICI.pythonanywhere.com` adresinde, HTTPS ile yayınlar.
Aşağıdaki komutlarda **KULLANICI** yerine kendi PythonAnywhere kullanıcı adını,
**REPO_URL** yerine GitHub depo adresini yaz.

---

## Önkoşullar
1. Bir **GitHub** hesabı.
2. Bir **PythonAnywhere** hesabı (ücretsiz "Beginner" yeterli): https://www.pythonanywhere.com
3. Bir **SECRET_KEY** üret (bilgisayarında, proje klasöründe venv açıkken):
   ```
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
   Çıkan uzun metni bir yere not al; canlı .env'de kullanacağız.

---

## Aşama 1 — Kodu GitHub'a gönder
Bilgisayarında proje klasöründe (venv açık), terminalde:
```
git init
git add .
git commit -m "Geek Panel - yayin"
```
> `db.sqlite3`, `.env` ve `media/` `.gitignore` sayesinde gönderilmez (test verin/şifren gizli kalır). Migration dosyaları ise gönderilir — bu doğrudur.

GitHub'da yeni boş bir depo aç (README ekleme), sonra:
```
git branch -M main
git remote add origin REPO_URL
git push -u origin main
```

---

## Aşama 2 — PythonAnywhere'de kodu indir ve ortam kur
PythonAnywhere panelinde **Consoles → Bash** ile bir konsol aç:
```
git clone REPO_URL personel_takip
cd personel_takip
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Aşama 3 — Web uygulamasını oluştur
1. Üstten **Web** sekmesi → **Add a new web app** → **Manual configuration** (Django değil, Manual) → **Python 3.12**.
2. Açılan sayfada:
   - **Virtualenv** bölümüne yolu yaz: `/home/KULLANICI/personel_takip/venv`
   - **Code → Working directory:** `/home/KULLANICI/personel_takip`
3. **WSGI configuration file** bağlantısına tıkla, içindeki her şeyi sil ve şunu yapıştır
   (KULLANICI'yı değiştir):
   ```python
   import os, sys
   path = '/home/KULLANICI/personel_takip'
   if path not in sys.path:
       sys.path.insert(0, path)
   os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
   from dotenv import load_dotenv
   load_dotenv(os.path.join(path, '.env'))
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
   Kaydet (Save).

---

## Aşama 4 — Canlı .env, veritabanı, statik dosyalar
Bash konsoluna dön (venv açık, klasör `personel_takip`):

`.env` dosyasını oluştur:
```
nano .env
```
İçine şunları yaz (SECRET_KEY'i Aşama 0'da ürettiğinle, KULLANICI'yı kendi adınla değiştir):
```
DJANGO_SECRET_KEY=buraya-urettigin-uzun-anahtar
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=KULLANICI.pythonanywhere.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://KULLANICI.pythonanywhere.com
DJANGO_SSL_REDIRECT=0
```
Kaydet: `Ctrl+O`, `Enter`, sonra çık: `Ctrl+X`.

Sonra veritabanı, statik ve medya:
```
python manage.py migrate
python manage.py collectstatic --noinput
mkdir -p media
python manage.py createsuperuser
```
(createsuperuser ile bir yönetici kullanıcı adı + şifre belirle — admin'e girmek için.)

---

## Aşama 5 — Statik & medya yolları + HTTPS
**Web** sekmesinde aşağı in, **Static files** bölümüne iki satır ekle:

| URL        | Directory                                         |
|------------|---------------------------------------------------|
| `/static/` | `/home/KULLANICI/personel_takip/staticfiles`      |
| `/media/`  | `/home/KULLANICI/personel_takip/media`            |

Aynı sayfada **Force HTTPS = Enabled** yap (kamera için şart).

En üstteki yeşil **Reload** düğmesine bas.

---

## Aşama 6 — İlk giriş ve kurulum
1. `https://KULLANICI.pythonanywhere.com/admin` → createsuperuser ile açtığın hesapla gir.
2. **Şubeler**'den şubeleri ekle.
3. **Personeller**'den, superuser hesabına bağlı, rolü **Genel Müdür** olan bir Personel oluştur
   (Kullanıcı Hesabı = superuser'ın, Şube = bir şube).
4. `https://KULLANICI.pythonanywhere.com` → artık panele girersin. Bundan sonra **Ekip**
   sekmesinden diğer yöneticileri (otomatik kullanıcı adı+şifre) ve şefleri (otomatik kod)
   ekleyebilirsin; admin'e bir daha girmen gerekmez.

---

## Güncelleme (ileride kod değişince)
Bilgisayarında: `git add . && git commit -m "guncelleme" && git push`
PythonAnywhere Bash:
```
cd personel_takip
source venv/bin/activate
git pull
python manage.py migrate
python manage.py collectstatic --noinput
```
Sonra Web sekmesinden **Reload**.

---

## Sık karşılaşılan sorunlar
- **DisallowedHost / Bad Request (400):** `.env` içindeki `DJANGO_ALLOWED_HOSTS` adresin tam
  `KULLANICI.pythonanywhere.com` olmalı. Düzeltip Reload.
- **CSRF 403 (form gönderince):** `DJANGO_CSRF_TRUSTED_ORIGINS=https://KULLANICI.pythonanywhere.com`
  satırı doğru mu? Reload.
- **Sayfa açılıyor ama tasarım bozuk (CSS yok):** `collectstatic` çalıştırıldı mı ve Static files
  yolları doğru mu? Reload.
- **Kamera açılmıyor:** Adrese `https://` ile giriyor musun ve Force HTTPS açık mı? Kamera yalnız
  HTTPS'te çalışır.
- **Bir şey çalışmazsa:** Web sekmesindeki **Error log** bağlantısı hatanın nedenini gösterir;
  oradaki son satırları bana iletebilirsin.
