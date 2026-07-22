from pathlib import Path
from datetime import timedelta
from decouple import config, Csv
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ── Application Definition ────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "storages",
   # "django_celery_beat",
    # Local apps
    "apps.users",
    "apps.products",
    "apps.inventory",
    "apps.orders",
    "apps.payments",
    "apps.reviews",
    "apps.wishlist",
    "apps.coupons",
    "apps.notifications",
    "apps.analytics",
    "cloudinary",
    "cloudinary_storage"
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ── Database ──────────────────────────────────────────────────────────────────
import dj_database_url

DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", default="postgres://localhost/maeckysounds"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ── Session ───────────────────────────────────────────────────────────────────
# Using database-backed sessions so guest carts persist across requests
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_NAME = "ms_session"
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True

# ── Custom User Model ─────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

# ── Password Hashing ──────────────────────────────────────────────────────────
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

# ── Static & Media ────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Sites ─────────────────────────────────────────────────────────────────────
SITE_ID = 1

# ── Allauth ───────────────────────────────────────────────────────────────────

ACCOUNT_ADAPTER = "apps.users.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.users.adapters.SocialAccountAdapter"

ACCOUNT_LOGIN_METHODS = {"email"}

ACCOUNT_SIGNUP_FIELDS = [
    "username*",
    "email*",
    "password1*",
    "password2*",
]

ACCOUNT_USER_MODEL_USERNAME_FIELD = "username"

ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_UNIQUE_EMAIL = True

SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_STORE_TOKENS = False

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email", "openid"],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
        "FETCH_USERINFO": True,
    }
}

LOGIN_REDIRECT_URL = "/api/v1/auth/google/finish/"
LOGOUT_REDIRECT_URL = "/"
# ── JWT ───────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("JWT_ACCESS_MINUTES", default=15, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("JWT_REFRESH_DAYS", default=7, cast=int)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_COOKIE": "ms_access",
    "AUTH_COOKIE_REFRESH": "ms_refresh",
    "AUTH_COOKIE_SECURE": config("COOKIE_SECURE", default=False, cast=bool),
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_PATH": "/",
    "AUTH_COOKIE_SAMESITE": "Lax",
}

# ── DRF ───────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.users.backends.CookieJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.products.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "200/day",
        "user": "2000/day",
        "auth": "10/minute",
        "search": "60/minute",
    },
    "EXCEPTION_HANDLER": "apps.users.exceptions.custom_exception_handler",
}

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="""
        http://localhost:3000,
        http://127.0.0.1:3000,
        http://localhost:5173,
        http://127.0.0.1:5173
    """,
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# ── CSRF ──────────────────────────────────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="""
        http://localhost:3000,
        http://127.0.0.1:3000,
        http://localhost:5173,
        http://127.0.0.1:5173,
        https://maeckysounds.netlify.app
    """,
    cast=Csv(),
)
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # Frontend must read and attach it

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "maecky-cache",
    }
}

# ── Celery ────────────────────────────────────────────────────────────────────
#CELERY_BROKER_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/0")
#CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://127.0.0.1:6379/0")
#CELERY_ACCEPT_CONTENT = ["json"]
#CELERY_TASK_SERIALIZER = "json"
#CELERY_RESULT_SERIALIZER = "json"
#CELERY_TIMEZONE = "Africa/Nairobi"
#CELERY_TASK_ALWAYS_EAGER = False
#CELERY_TASK_EAGER_PROPAGATES = True

# ── Storage ───────────────────────────────────────────────────────────────────
# USE_S3 = config("AWS_ACCESS_KEY_ID", default="") != ""

# if USE_S3:
#     DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
#     AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
#     AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
#     AWS_STORAGE_BUCKET_NAME = config("AWS_BUCKET_NAME", default="")
#     AWS_S3_REGION_NAME = config("AWS_REGION", default="us-east-1")
#     AWS_S3_FILE_OVERWRITE = False
#     AWS_DEFAULT_ACL = "public-read"
#     AWS_S3_CUSTOM_DOMAIN = f"{config('AWS_BUCKET_NAME', default='')}.s3.amazonaws.com"
#     MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = "Maecky Sounds <noreply@maeckysounds.co.ke>"
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ── Frontend ──────────────────────────────────────────────────────────────────
FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:3000")

# ── M-Pesa ────────────────────────────────────────────────────────────────────
MPESA_CONSUMER_KEY = config("MPESA_CONSUMER_KEY", default="")
MPESA_CONSUMER_SECRET = config("MPESA_CONSUMER_SECRET", default="")
MPESA_SHORTCODE = config("MPESA_SHORTCODE", default="174379")
MPESA_PASSKEY = config("MPESA_PASSKEY", default="")
MPESA_ENVIRONMENT = config("MPESA_ENVIRONMENT", default="sandbox")
MPESA_CALLBACK_URL = config(
    "MPESA_CALLBACK_URL",
    default="http://localhost:8000/api/v1/payments/mpesa/callback/",
)

# ── Stripe ────────────────────────────────────────────────────────────────────
STRIPE_PUBLIC_KEY = config("STRIPE_PUBLIC_KEY", default="")
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")

# ── Business Logic ────────────────────────────────────────────────────────────
LOW_STOCK_THRESHOLD = config("LOW_STOCK_THRESHOLD", default=5, cast=int)
FREE_SHIPPING_MINIMUM = config("FREE_SHIPPING_MINIMUM", default=10000, cast=int)

# ── Admin URL ─────────────────────────────────────────────────────────────────
ADMIN_URL = "store-management/"

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": config("CLOUDINARY_CLOUD_NAME", default=""),
    "API_KEY": config("CLOUDINARY_API_KEY", default=""),
    "API_SECRET": config("CLOUDINARY_API_SECRET", default=""),
}

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

