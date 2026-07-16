from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(name="apps.inventory.tasks.check_low_stock_alerts")
def check_low_stock_alerts():
    """
    Periodic task: scan all inventory records and alert
    admin for any products that are low on stock.
    """
    from .models import Inventory
    from apps.notifications.tasks import send_low_stock_alert

    low_stock_items = Inventory.objects.filter(
        track_inventory=True,
    ).select_related("product")

    alerted = 0
    for inv in low_stock_items:
        if inv.is_low_stock:
            send_low_stock_alert.delay(str(inv.product.id))
            alerted += 1

    logger.info(f"Low stock check complete. Alerted for {alerted} products.")
    return {"alerted": alerted}