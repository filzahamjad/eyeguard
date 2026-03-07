"""
Merged Django settings for the `eyeguard` project.

This file merges the original project scaffold settings (sqlite, basic
middleware and templates) with the surveillance-focused additions
(REST framework, CORS, media/static configuration) from the
attachment. Keep secrets and deployment-specific overrides out of
version control in production.
"""

import os
from pathlib import Path

# Load .env from project root so POSTGRES_* / DB_* are available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
except ImportError:
    pass

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY (development)
# NOTE: Do not commit production secrets. Move them to environment
# variables or a secrets manager for deployed environments.
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-icqfk+#x47&(pk3g$2i-hbud9g244i0gnq7i80d7hyv8l+ko02')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '0.0.0.0', '*']


# Application definition

INSTALLED_APPS = [
    'daphne',  # ASGI server for WebSockets (must be first)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'corsheaders',
    'channels',  # WebSocket support

    # Local app
    'eyeguard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files under Daphne/ASGI
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'eyeguard.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates")],
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

WSGI_APPLICATION = 'eyeguard.wsgi.application'


# Database
# Default: SQLite (zero-install, fully portable — database file stored next to the app).
# To use PostgreSQL instead, set DB_ENGINE=postgresql in a .env file (or environment)
# along with POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_HOST / POSTGRES_PORT.
_db_engine = os.environ.get('DB_ENGINE', '').lower()

if _db_engine in ('postgresql', 'postgres', 'django.db.backends.postgresql'):
    # PostgreSQL — requires a running PostgreSQL server on the target machine.
    DATABASES = {
        'default': {
            'ENGINE': 'eyeguard.postgresql13_backend',
            'NAME': os.environ.get('POSTGRES_DB') or os.environ.get('DB_NAME', 'eyeguard'),
            'USER': os.environ.get('POSTGRES_USER') or os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD') or os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('POSTGRES_HOST') or os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('POSTGRES_PORT') or os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    # SQLite — no installation required, database file lives in the project directory.
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
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
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static & media
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# File upload limits (keep modest for dev)
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# Create media subdirectories used by surveillance features
os.makedirs(os.path.join(MEDIA_ROOT, 'alerts'), exist_ok=True)
os.makedirs(os.path.join(MEDIA_ROOT, 'models'), exist_ok=True)


# Django REST Framework defaults used in this project
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
}


# CORS config for local frontend integration
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:8080',
]


# Django Channels WebSocket configuration
ASGI_APPLICATION = 'eyeguard.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],  # Redis server
        },
    },
}

# Alternative: In-memory channel layer (development only, single-process)
# Note: This won't work with multiple worker processes in production
# Uncomment below if Redis is not available:
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels.layers.InMemoryChannelLayer',
#     },
# }


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login redirect for @login_required (e.g. /live-detection/ page)
LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/live-detection/'

