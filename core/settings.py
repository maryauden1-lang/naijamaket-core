"""
Django settings for core project.
Configured for NaijaSale production with Coolify, SQLite, and Backblaze B2.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-naijasale-local-dev-key')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'naijasale.com',
    'www.naijasale.com',
    '.naijasale.com',
    '*',
]

CSRF_TRUSTED_ORIGINS = [
    'https://naijasale.com',
    'https://www.naijasale.com',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.humanize',

    # Third-party apps
    'axes',
    'storages',  # Required for Backblaze B2 S3 storage

    # Local application
    'marketplace.apps.MarketplaceConfig',
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
    'axes.middleware.AxesMiddleware',
    'marketplace.middleware.ActiveUserMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'marketplace' / 'templates' / 'marketplace',
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ==============================================================================
# DATABASE CONFIGURATION
# Automatically uses /app/data/db.sqlite3 on the server if present,
# otherwise falls back to local db.sqlite3 on your laptop.
# ==============================================================================
DATA_DIR = BASE_DIR / 'data'
if (DATA_DIR / 'db.sqlite3').exists():
    DB_PATH = DATA_DIR / 'db.sqlite3'
else:
    DB_PATH = BASE_DIR / 'db.sqlite3'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DB_PATH,
    }
}

# Database cache for visitor tracking
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'naijasale_cache_table',
        'TIMEOUT': 300,
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Axes security
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = None

# Localization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Icons)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ==============================================================================
# BACKBLAZE B2 STORAGE CONFIGURATION
# Directly maps to bucket root without adding /media/ prefix
# ==============================================================================
BUCKET_NAME = (
    os.environ.get('AWS_STORAGE_BUCKET_NAME')
    or os.environ.get('AWS_S3_BUCKET_NAME')
    or os.environ.get('BACKBLAZE_BUCKET_NAME')
)

ACCESS_KEY = (
    os.environ.get('AWS_ACCESS_KEY_ID')
    or os.environ.get('BACKBLAZE_KEY_ID')
)

SECRET_KEY_B2 = (
    os.environ.get('AWS_SECRET_ACCESS_KEY')
    or os.environ.get('BACKBLAZE_APPLICATION_KEY')
)

ENDPOINT_URL = (
    os.environ.get('AWS_S3_ENDPOINT_URL')
    or os.environ.get('BACKBLAZE_S3_ENDPOINT')
    or 'https://s3.us-east-005.backblazeb2.com'
)

if BUCKET_NAME and ACCESS_KEY and SECRET_KEY_B2:
    AWS_ACCESS_KEY_ID = ACCESS_KEY
    AWS_SECRET_ACCESS_KEY = SECRET_KEY_B2
    AWS_STORAGE_BUCKET_NAME = BUCKET_NAME
    AWS_S3_ENDPOINT_URL = ENDPOINT_URL

    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.{AWS_S3_ENDPOINT_URL.replace('https://', '')}"
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = False

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {},
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
else:
    # Local fallback for development on laptop
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SESSION_COOKIE_AGE = 86400 * 30
SESSION_SAVE_EVERY_REQUEST = True