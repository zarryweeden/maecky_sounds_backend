from .base import *

DEBUG = True

INSTALLED_APPS += ["debug_toolbar"]

MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE

INTERNAL_IPS = ["127.0.0.1"]

# Use local file storage in development
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Log all emails to console in dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Eager Celery tasks in dev so they run synchronously
CELERY_TASK_ALWAYS_EAGER = True

# Relaxed password validation in dev
AUTH_PASSWORD_VALIDATORS = []

# Show SQL queries in dev
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
        },
    },
}