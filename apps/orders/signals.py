from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order


@receiver(post_save, sender=Order)
def handle_order_status_change(sender, instance, created, **kwargs):
    """
    Fire appropriate Celery tasks when order status changes.
    """
    if created:
        # New order — confirmation email is triggered from the view
        # after payment instructions are returned
        return

    if instance.status == Order.Status.SHIPPED and instance.tracking_number:
        from apps.notifications.tasks import send_shipping_update_email
        send_shipping_update_email.delay(
            str(instance.id),
            instance.tracking_number,
        )