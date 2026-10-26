import logging
import os
import secrets
from pathlib import Path
from urllib.parse import unquote, urlparse

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

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
    ).split(",")
    if host.strip()
]


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
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
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
            "class": "logging.FileHandler",
            "formatter": "main_format",
            "filename": "app.logs",
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

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TINKOFF_TOKEN = os.environ.get("TINKOFF_TOKEN", "")

"""Celery Configuration Options"""
CELERY_TIMEZONE = "Europe/Moscow"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
# CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672'
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
PRICE_UPDATE_INTERVAL_SECONDS = max(
    10.0, float(os.environ.get("PRICE_UPDATE_INTERVAL_SECONDS", "60"))
)

"""Debug Celery"""
CELERY_TASK_ALWAYS_EAGER = False
