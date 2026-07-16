import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("maeckysounds")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "check-abandoned-carts": {
        "task": "apps.notifications.tasks.send_abandoned_cart_emails",
        "schedule": crontab(hour=10, minute=0),
    },
    "check-low-stock": {
        "task": "apps.inventory.tasks.check_low_stock_alerts",
        "schedule": crontab(hour="*/6"),
    },
}