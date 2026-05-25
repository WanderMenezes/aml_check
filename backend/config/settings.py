"""Enterprise settings for the AML/KYC compliance platform."""

from importlib.util import find_spec
from pathlib import Path

from common.utils.env import env, env_bool, env_int, env_list, load_env_file

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

load_env_file(ROOT_DIR / ".env")

if find_spec("pymysql"):
    import pymysql

    pymysql.install_as_MySQLdb()
    pymysql.version_info = (2, 2, 1, "final", 0)
    pymysql.__version__ = "2.2.1"

SECRET_KEY = env("DJANGO_SECRET_KEY", "change-me-for-production")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    ["http://localhost:3000", "http://127.0.0.1:3000"],
)
APP_NAME = "AML Check Enterprise"
APP_URL = env("APP_URL", "http://127.0.0.1:8000")
FRONTEND_URL = env("FRONTEND_URL", "http://127.0.0.1:3000")

CORE_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = ["rest_framework"]
if find_spec("drf_spectacular"):
    THIRD_PARTY_APPS.append("drf_spectacular")

LOCAL_APPS = [
    "apps.users.apps.UsersConfig",
    "apps.intelligence.apps.IntelligenceConfig",
    "apps.screening.apps.ScreeningConfig",
    "apps.audit.apps.AuditConfig",
]

INSTALLED_APPS = CORE_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "common.middleware.security.CORSMiddleware",
    "common.middleware.request_context.RequestIDMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "common.middleware.request_context.LocaleHeaderMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "common.middleware.security.RateLimitMiddleware",
    "common.middleware.security.SecurityHeadersMiddleware",
    "common.middleware.request_context.AuditContextMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

MYSQL_READY = bool(find_spec("MySQLdb") or find_spec("pymysql"))
DB_ENGINE = env("DB_ENGINE", "mysql")

if DB_ENGINE.lower() == "mysql" and MYSQL_READY:
    DATABASES = {
        "default": {
            "ENGINE": "common.db.mysql_compat",
            "NAME": env("DB_NAME", "aml_check"),
            "USER": env("DB_USER", "root"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "127.0.0.1"),
            "PORT": env("DB_PORT", "3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

CACHE_USE_REDIS = env_bool("CACHE_USE_REDIS", True) and bool(find_spec("redis"))
if CACHE_USE_REDIS:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": env("REDIS_URL", "redis://127.0.0.1:6379/1"),
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "aml-check-cache",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "users.User"

LANGUAGE_CODE = "pt"
LANGUAGES = [
    ("pt", "Português"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = env("APP_TIMEZONE", "Africa/Sao_Tome")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "noreply@aml-check.local")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "common.auth.authentication.JWTAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "common.schemas.openapi.StableAutoSchema",
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": env_int("API_PAGE_SIZE", 20),
}

SPECTACULAR_SETTINGS = {
    "TITLE": APP_NAME,
    "DESCRIPTION": "AML / KYC / Compliance screening platform",
    "VERSION": "1.0.0",
}

JWT_SETTINGS = {
    "ACCESS_TTL_MINUTES": env_int("JWT_ACCESS_TTL_MINUTES", 30),
    "REFRESH_TTL_DAYS": env_int("JWT_REFRESH_TTL_DAYS", 7),
    "ALGORITHM": "HS256",
    "ISSUER": APP_NAME,
}

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SCREENING_SETTINGS = {
    "MAX_RESULTS": env_int("SCREENING_MAX_RESULTS", 20),
    "MIN_FUZZY_SCORE": env_int("SCREENING_MIN_FUZZY_SCORE", 70),
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "sync-watchlists-daily": {
        "task": "apps.intelligence.tasks.sync_enabled_sources_task",
        "schedule": 60 * 60 * 24,
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        }
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
