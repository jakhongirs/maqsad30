import logging
import os
from pathlib import Path

import environ
import sentry_sdk
from celery.schedules import crontab

from core.jazzmin_conf import *  # noqa

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# READING ENV
env = environ.Env()
env.read_env(os.path.join(BASE_DIR, ".env"))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG")

ALLOWED_HOSTS = ["*"]

# Application definition
DJANGO_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

CUSTOM_APPS = [
    "apps.common",
    "apps.users",
    "apps.onboarding",
    "apps.main",
    "apps.telegram_bot",
    "apps.notification",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "drf_yasg",
    "corsheaders",
    "modeltranslation",
    "nplusone.ext.django",
    "django_celery_beat",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.users.authentication.TelegramAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 10,
    "LANGUAGE_QUERY_PARAMETER": "lang",
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
}

INSTALLED_APPS = DJANGO_APPS + CUSTOM_APPS + THIRD_PARTY_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "nplusone.ext.django.NPlusOneMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "core.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": env.str("DB_ENGINE"),
        "NAME": env.str("DB_NAME"),
        "USER": env.str("DB_USER"),
        "PASSWORD": env.get_value("DB_PASSWORD"),
        "HOST": env.str("DB_HOST"),
        "PORT": env.str("DB_PORT"),
        "ATOMIC_REQUESTS": True,
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

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

AUTH_USER_MODEL = "users.User"

NPLUSONE_LOGGER = logging.getLogger("nplusone")
NPLUSONE_LOG_LEVEL = logging.WARN

LOGGING = {
    "version": 1,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "nplusone": {
            "handlers": ["console"],
            "level": "WARN",
        },
    },
}

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "uz"

LANGUAGES = (
    ("en", "English"),
    ("uz", "Uzbek"),
    ("ru", "Russian"),
    ("uz-cy", "Uzbek (Cyrillic)"),
)

LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = "Asia/Tashkent"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "static"
STATICFILES_DIRS = (BASE_DIR / "staticfiles",)

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CACHES
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"{env.str('REDIS_URL', 'redis://localhost:6379/0')}",
        "KEY_PREFIX": "boilerplate",  # todo: you must change this with your project name or something else
    }
}

REDIS_HOST = env.str("REDIS_HOST", "localhost")
REDIS_PORT = env.int("REDIS_PORT", 6379)
REDIS_DB = env.int("REDIS_DB", 0)


# CELERY CONFIGURATION
CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env.str("CELERY_BROKER_URL", "redis://localhost:6379/0")

CELERY_TIMEZONE = "Asia/Tashkent"

CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

# Celery Beat Schedule
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CELERY_BEAT_SCHEDULE = {
    # Update channel membership status - run once a day at midnight
    "update-channel-membership-status": {
        "task": "apps.users.tasks.update_channel_membership_status",
        "schedule": crontab(hour=0, minute=0),
    },
    "update-user-challenge-streaks": {
        "task": "apps.main.tasks.update_all_user_challenge_streaks",
        "schedule": crontab(hour=0, minute=5),
    },
    # Challenge notifications - run at 05:00, 19:00 and 20:00
    "send-challenge-notifications-05": {
        "task": "apps.notification.tasks.send_challenge_notifications",
        "schedule": crontab(hour=5, minute=0),
    },
    "send-challenge-notifications-19": {
        "task": "apps.notification.tasks.send_challenge_notifications",
        "schedule": crontab(hour=19, minute=0),
    },
    "send-challenge-notifications-20": {
        "task": "apps.notification.tasks.send_challenge_notifications",
        "schedule": crontab(hour=20, minute=0),
    },
    # Super challenge general notifications - run once a day at 21:00
    "send-super-challenge-general-notifications": {
        "task": "apps.notification.tasks.send_super_challenge_general_notifications",
        "schedule": crontab(hour=21, minute=0),
    },
    # Send super challenge progress notifications - run once a day at 00:30
    "send-super-challenge-progress-notifications": {
        "task": "apps.notification.tasks.send_super_challenge_progress_notifications",
        "schedule": crontab(hour=0, minute=30),
    },
}

sentry_sdk.init(
    dsn="https://e261deeaf0d829693b6f2be7d3517906@o4508913256890368.ingest.us.sentry.io/4508913259642880",
    send_default_pii=True,
    traces_sample_rate=1.0,
    _experiments={
        "continuous_profiling_auto_start": True,
    },
)

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN = "7217412861:AAEq1F5tHwiSLqtDMqccFTNarlFYl4xdzX0"
TELEGRAM_CHANNEL_ID = "-1002128930156"
WEB_APP_URL = "https://maqsad30.icc-kimyo.uz/"
