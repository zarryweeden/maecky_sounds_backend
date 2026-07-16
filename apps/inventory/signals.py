from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Inventory


@receiver(post_save, sender=Inventory)
def check_low_stock_on_save(sender, instance, **kwargs):
    """
    When inventory is saved and stock is low,
    queue a low-stock alert email to admin.
    """
    if instance.track_inventory and instance.is_low_stock:
        from apps.notifications.tasks import send_low_stock_alert
        send_low_stock_alert.delay(str(instance.product.id))