"""
Django settings for core project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-9xps_@o)+#=h7$9lnn^b_gdj6*k2%!!p9)m*%0zv66&4!hhl48')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')

# Allowed hosts (wildcard removed for production host-header security)
ALLOWED_HOSTS = [
    'naijasale.com',
    'www.naijasale.com',
    '199.247.22.119',
    'olhbbbatpfblic7yhycinpvh.199.247.22.119.sslip.io',
    'localhost',
    '127.0.0.1',
]

# CSRF trusted origins for Coolify domain proxies and custom domain
CSRF_TRUSTED_ORIGINS = [
    'https://naijasale.com',
    'https://www.naijasale.com',
    'http://naijasale.com',
    'http://www.naijasale.com',
    'http://*.sslip.io',
    'https://*.sslip.io',
    'http://olhbbbatpfblic7yhycinpvh.199.247.22.119.sslip.io',
    'https://olhbbbatpfblic7yhycinpvh.199.247.22.119.sslip.io',
    'http://localhost',
    'http://127.0.0.1',
]

# Reverse proxy support (Coolify / Traefik)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Security Headers & Cookie Protection
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Defense against Session Hijacking, Clickjacking, and MIME-sniffing
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sitemaps',  # Enables automated dynamic XML sitemap generation
    
    # Brute-force login defense
    'axes',
    
    # Third-party storage backend
    'storages',
    
    # Custom apps
    'marketplace',
]

# Authentication Backends (Axes checks failed attempts before passing to standard auth)
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',  # Must be at the bottom
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'marketplace' / 'templates' / 'marketplace',
            BASE_DIR / 'marketplace' / 'templates',
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATA_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Lagos'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ==============================================================================
# BACKBLAZE B2 & CLOUDFLARE MEDIA STORAGE CONFIGURATION
# ==============================================================================
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'naijasale-media-prod')
AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', 'https://s3.us-east-005.backblazeb2.com')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-005')
AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN', 'media.naijasale.com')

AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False

# Django STORAGES engine (Static files via WhiteNoise, User Media via Backblaze/Cloudflare)
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media URL and Media Root (Explicitly locked to the media/ folder)
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Staff Workspace & Authentication Routing
LOGIN_REDIRECT_URL = '/workspace/routing/'
LOGIN_URL = '/portal-management-99/login/'

# ==============================================================================
# BREVO EMAIL ENGINE CONFIGURATION
# ==============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp-relay.brevo.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'c1ec8c001@smtp-brevo.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'xsmtpsib-603eda44a21b10ae5e77199571825d3bcdbc9300942d90b4836734eec563b41b-KO1uO9QHMsBaTIS4')
DEFAULT_FROM_EMAIL = 'Naijasale <support@naijasale.com>'
SERVER_EMAIL = 'support@naijasale.com'

# ==============================================================================
# AXES BRUTE-FORCE SECURITY SETTINGS
# ==============================================================================
AXES_FAILURE_LIMIT = 5                      # Lock out after 5 wrong attempts
AXES_COOLOFF_TIME = 0.5                     # Lockout lasts for 0.5 hours (30 minutes)
AXES_RESET_ON_SUCCESS = True               # Clear failed counter on good login
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True
AXES_IPWARE_META_PRECEDENCE_ORDER = (       # Detects real visitor IP behind Cloudflare
    'HTTP_CF_CONNECTING_IP',
    'HTTP_X_FORWARDED_FOR',
    'REMOTE_ADDR',
)