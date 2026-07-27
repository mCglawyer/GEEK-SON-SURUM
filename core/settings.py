import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

def env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ('1', 'true', 'yes', 'on')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
DEBUG = env_bool('DJANGO_DEBUG', default=False)

if not SECRET_KEY:
    if DEBUG:
        from django.core.management.utils import get_random_secret_key
        SECRET_KEY = get_random_secret_key()
    else:
        raise RuntimeError(
            "DJANGO_SECRET_KEY tanımlı değil. Canlı ortamda çalışmadan önce "
            ".env dosyasında ayarlayın."
        )

_allowed = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(',') if h.strip()]
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

_csrf = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf.split(',') if o.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',
    'panel',
]

MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'panel.middleware.EgitimKapiMiddleware',
]

ROOT_URLCONF = 'core.urls'
CSRF_FAILURE_VIEW = 'panel.views.csrf_hata_sayfasi'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'panel.context_processors.bildirim_ctx',
                'panel.context_processors.kalibrasyon_uyari_ctx',
                'panel.context_processors.egitim_ctx',
                'panel.context_processors.sube_secici_ctx',
                'panel.context_processors.acilis_ctx',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

if os.environ.get('DB_NAME'):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
    }

    _sslmode = os.environ.get('DB_SSLMODE')
    if _sslmode:
        DATABASES['default']['OPTIONS'] = {'sslmode': _sslmode}

# Geçici ikinci bağlantı: sadece Oregon'a veri taşıma sırasında, Render Shell'den
# kullanılır. Bu ortam değişkenleri tanımlı değilse hiçbir etkisi yok — canlı
# sitenin kullandığı 'default' bağlantıya asla dokunmaz.
if os.environ.get('OREGON_DB_HOST'):
    DATABASES['oregon'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('OREGON_DB_NAME', 'neondb'),
        'USER': os.environ.get('OREGON_DB_USER', ''),
        'PASSWORD': os.environ.get('OREGON_DB_PASSWORD', ''),
        'HOST': os.environ.get('OREGON_DB_HOST', ''),
        'PORT': os.environ.get('OREGON_DB_PORT', '5432'),
        'CONN_MAX_AGE': 0,
        'OPTIONS': {'sslmode': 'require'},
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- Depolama (Storages) ---
# Statik dosyalar (CSS/JS/görsel) her zaman whitenoise ile sunucunun kendisinden sunulur
# (PythonAnywhere'deki gibi ayrı bir "static files mapping" gerektirmez, Render/başka
# platformlarda da sorunsuz çalışır).
#
# Medya (kullanıcı yüklemeleri: fotoğraf, PDF, video) için: R2_* ortam değişkenleri
# tanımlıysa Cloudflare R2 (S3 uyumlu) kullanılır; tanımlı değilse eskisi gibi sunucunun
# yerel diski kullanılır. Yani bu ayar R2 bilgileri girilmeden HİÇBİR ŞEYİ DEĞİŞTİRMEZ —
# mevcut PythonAnywhere kurulumu bu haliyle de sorunsuz çalışmaya devam eder.
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

R2_BUCKET = os.environ.get('R2_BUCKET', '')
R2_ACCESS_KEY = os.environ.get('R2_ACCESS_KEY', '')
R2_SECRET_KEY = os.environ.get('R2_SECRET_KEY', '')
R2_ENDPOINT_URL = os.environ.get('R2_ENDPOINT_URL', '')
R2_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL', '')  # ör: https://medya.geekpanel.net veya https://pub-xxx.r2.dev

if R2_BUCKET and R2_ACCESS_KEY and R2_SECRET_KEY and R2_ENDPOINT_URL:
    STORAGES['default'] = {'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage'}
    AWS_ACCESS_KEY_ID = R2_ACCESS_KEY
    AWS_SECRET_ACCESS_KEY = R2_SECRET_KEY
    AWS_STORAGE_BUCKET_NAME = R2_BUCKET
    AWS_S3_ENDPOINT_URL = R2_ENDPOINT_URL
    AWS_S3_ADDRESSING_STYLE = 'virtual'
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False
    if R2_PUBLIC_URL:
        AWS_S3_CUSTOM_DOMAIN = R2_PUBLIC_URL.replace('https://', '').replace('http://', '').rstrip('/')
else:
    STORAGES['default'] = {'BACKEND': 'django.core.files.storage.FileSystemStorage'}

DATA_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('DJANGO_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', '1') == '1'
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@geekpanel.net')

# --- Web Push (VAPID) ---
VAPID_PUBLIC_KEY = os.environ.get(
    'VAPID_PUBLIC_KEY',
    'BC65Z7BXa5XLsUA86fC7NU3ocCF1gd9JuPkhkutdN_EFN3dIGpP4Jlmq7ImmOCOvpV0vfINfEJj2iowBgttJZ5c')
# Render gibi platformlarda kalıcı dosya sistemi garanti olmadığı için, anahtarın ham içeriği
# ortam değişkeniyle de verilebilir. Kopyalarken satır sonlarının (\n) bozulması çok yaygın bir
# sorun olduğu için EN GÜVENİLİR yöntem VAPID_PRIVATE_KEY_B64 (anahtarın base64 hâli, tek satır,
# satır sonu/boşluk içermez). VAPID_PRIVATE_KEY_PEM (ham \n'li metin) eski uyumluluk için hâlâ
# destekleniyor. İkisi de yoksa PythonAnywhere'deki gibi dosya yolu kullanılır.
_vapid_b64 = os.environ.get('VAPID_PRIVATE_KEY_B64', '')
_vapid_pem = os.environ.get('VAPID_PRIVATE_KEY_PEM', '')
if _vapid_b64:
    import base64 as _b64
    VAPID_PRIVATE_KEY = _b64.b64decode(_vapid_b64).decode('utf-8')
elif _vapid_pem:
    VAPID_PRIVATE_KEY = _vapid_pem.replace('\\n', '\n')
else:
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY_PATH', str(BASE_DIR / 'private_key.pem'))
VAPID_CLAIMS = {'sub': 'mailto:info@geekcoffeeshop.com'}
