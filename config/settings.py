import logging
import os
import secrets
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() in {"1", "true", "yes"}
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Set DJANGO_SECRET_KEY when DEBUG is disabled")
    SECRET_KEY = secrets.token_urlsafe(50)

SECURE_SSL_REDIRECT = os.environ.get(
    "DJANGO_SECURE_SSL_REDIRECT", str(not DEBUG)
).lower() in {"1", "true", "yes"}
SESSION_COOKIE_SECURE = os.environ.get(
    "DJANGO_SECURE_COOKIES", str(not DEBUG)
).lower() in {"1", "true", "yes"}
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_HSTS_SECONDS = int(
    os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0")
)
if os.environ.get("DJANGO_TRUST_X_FORWARDED_PROTO", "false").lower() in {
    "1",
    "true",
    "yes",
}:
    # Enable only when a trusted reverse proxy overwrites this header.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

allowed_hosts_setting = os.environ.get("DJANGO_ALLOWED_HOSTS")
if allowed_hosts_setting is None:
    if not DEBUG:
        raise ImproperlyConfigured(
            "Set DJANGO_ALLOWED_HOSTS when DEBUG is disabled"
        )
    allowed_hosts_setting = "localhost,127.0.0.1,testserver"
ALLOWED_HOSTS = [
    host.strip() for host in allowed_hosts_setting.split(",") if host.strip()
]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must contain at least one host")
AUTH_RATE_LIMIT_IP_HEADER = os.environ.get(
    "DJANGO_AUTH_RATE_LIMIT_IP_HEADER", "REMOTE_ADDR"
)


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dashboard",
    "user",
    "rest_framework",
    "django_filters",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "user.api_authentication.RateLimitedBasicAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": (
        "dashboard.api.v1.pagination.BoundedLimitOffsetPagination"
    ),
    "PAGE_SIZE": 100,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "backtest": "20/hour",
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "main_format": {
            "format": "[{module} {asctime} {levelname}] {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "main_format"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "main_format",
            "filename": "app.logs",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "main": {"handlers": ["console", "file"], "level": "INFO", "propagate": True}
    },
}

logger = logging.getLogger("main")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
LOGIN_URL = "user:auth"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

database_url = os.environ.get("DATABASE_URL")
if database_url:
    database = urlparse(database_url)
    if database.scheme in {"postgres", "postgresql"}:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": database.path.lstrip("/"),
                "USER": unquote(database.username or ""),
                "PASSWORD": unquote(database.password or ""),
                "HOST": database.hostname or "localhost",
                "PORT": str(database.port or 5432),
                "CONN_MAX_AGE": 60,
                "OPTIONS": dict(parse_qsl(database.query, keep_blank_values=True)),
            }
        }
    elif database.scheme == "sqlite":
        if database_url.startswith("sqlite:////"):
            sqlite_name = "/" + database_url.removeprefix("sqlite:////")
        else:
            sqlite_name = str(BASE_DIR / unquote(database.path).lstrip("/"))
        DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": sqlite_name}}
    else:
        raise ValueError("DATABASE_URL must use postgres, postgresql or sqlite scheme")
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TINKOFF_TOKEN = os.environ.get("TINKOFF_TOKEN", "")

"""Celery Configuration Options"""
CELERY_TIMEZONE = "Europe/Moscow"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
# CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672'
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CACHE_URL = os.environ.get("DJANGO_CACHE_URL")
if CACHE_URL is None and not DEBUG and CELERY_BROKER_URL.startswith(
    ("redis://", "rediss://")
):
    CACHE_URL = CELERY_BROKER_URL

TASK_LOCK_REDIS_URL = os.environ.get("TASK_LOCK_REDIS_URL") or CACHE_URL
if TASK_LOCK_REDIS_URL is None and CELERY_BROKER_URL.startswith(
    ("redis://", "rediss://")
):
    TASK_LOCK_REDIS_URL = CELERY_BROKER_URL
if TASK_LOCK_REDIS_URL and not TASK_LOCK_REDIS_URL.startswith(
    ("redis://", "rediss://")
):
    raise ImproperlyConfigured("TASK_LOCK_REDIS_URL must use redis or rediss scheme")

if CACHE_URL:
    if not CACHE_URL.startswith(("redis://", "rediss://")):
        raise ImproperlyConfigured("DJANGO_CACHE_URL must use redis or rediss scheme")
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": CACHE_URL,
            "KEY_PREFIX": "investing",
        }
    }
elif DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "investing-local-cache",
        }
    }
else:
    raise ImproperlyConfigured(
        "Set DJANGO_CACHE_URL to a shared Redis cache when DEBUG is disabled"
    )

PRICE_UPDATE_INTERVAL_SECONDS = max(
    10.0, float(os.environ.get("PRICE_UPDATE_INTERVAL_SECONDS", "60"))
)

"""Debug Celery"""
CELERY_TASK_ALWAYS_EAGER = False
