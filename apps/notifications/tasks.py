"""
Celery tasks for all async notifications.
Each task is idempotent and logs errors without crashing.
"""
import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.notifications.tasks.send_order_confirmation_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_order_confirmation_email(self, order_id: str):
    """Send an order confirmation email after successful order placement."""
    try:
        from apps.orders.models import Order
        from .emails import send_order_confirmation

        order = Order.objects.prefetch_related("items").get(id=order_id)
        success = send_order_confirmation(order)

        if not success:
            raise Exception(f"send_order_confirmation returned False for order {order_id}")

        logger.info(f"Order confirmation email sent for {order.order_number}")

    except Exception as exc:
        logger.error(f"send_order_confirmation_email failed for {order_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    name="apps.notifications.tasks.send_shipping_update_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_shipping_update_email(self, order_id: str, tracking_number: str):
    """Notify the customer that their order has shipped."""
    try:
        from apps.orders.models import Order
        from .emails import send_shipping_update

        order = Order.objects.get(id=order_id)
        send_shipping_update(order, tracking_number)
        logger.info(f"Shipping update email sent for {order.order_number}")

    except Exception as exc:
        logger.error(f"send_shipping_update_email failed for {order_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    name="apps.notifications.tasks.send_low_stock_alert",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def send_low_stock_alert(self, product_id: str):
    """Email admin when a product drops to or below the low-stock threshold."""
    try:
        from apps.products.models import Product
        from .emails import send_low_stock_alert_email
        from django.contrib.auth import get_user_model

        User = get_user_model()
        product = Product.objects.select_related("inventory").get(id=product_id)

        # Send to all admin users
        admin_emails = list(
            User.objects.filter(is_staff=True, is_active=True)
            .values_list("email", flat=True)
        )

        if not admin_emails:
            admin_emails = [settings.DEFAULT_FROM_EMAIL]

        for email in admin_emails:
            send_low_stock_alert_email(product, email)

        logger.info(
            f"Low stock alert sent for '{product.name}' "
            f"(available: {product.inventory.available}) to {admin_emails}"
        )

    except Exception as exc:
        logger.error(f"send_low_stock_alert failed for product {product_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(name="apps.notifications.tasks.send_welcome_email")
def send_welcome_email(user_id: str):
    """Send a welcome email to a newly registered user."""
    try:
        from django.contrib.auth import get_user_model
        from .emails import send_welcome

        User = get_user_model()
        user = User.objects.get(id=user_id)
        send_welcome(user)
        logger.info(f"Welcome email sent to {user.email}")

    except Exception as exc:
        logger.error(f"send_welcome_email failed for user {user_id}: {exc}")


@shared_task(name="apps.notifications.tasks.send_password_reset_email")
def send_password_reset_email(user_id: str, reset_url: str):
    """Send a password reset link email."""
    try:
        from django.contrib.auth import get_user_model
        from .emails import send_password_reset

        User = get_user_model()
        user = User.objects.get(id=user_id)
        send_password_reset(user, reset_url)
        logger.info(f"Password reset email sent to {user.email}")

    except Exception as exc:
        logger.error(f"send_password_reset_email failed for user {user_id}: {exc}")


@shared_task(name="apps.notifications.tasks.send_abandoned_cart_emails")
def send_abandoned_cart_emails():
    """
    Daily Celery Beat task.
    Find carts with items that have not been touched in 24+ hours
    and whose owner has not placed an order since.
    Send a gentle reminder email to recover the sale.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.orders.models import Cart
    from .emails import send_abandoned_cart_email

    cutoff = timezone.now() - timedelta(hours=24)

    abandoned_carts = (
        Cart.objects.filter(
            is_active=True,
            updated_at__lte=cutoff,
            user__isnull=False,
        )
        .prefetch_related("items__product")
        .select_related("user")
    )

    sent = 0
    for cart in abandoned_carts:
        if not cart.items.exists():
            continue

        # Skip users who placed an order recently
        from apps.orders.models import Order
        recent_order = Order.objects.filter(
            user=cart.user,
            created_at__gte=cutoff,
        ).exists()

        if recent_order:
            continue

        try:
            send_abandoned_cart_email(cart.user, cart)
            sent += 1
        except Exception as e:
            logger.error(f"Abandoned cart email failed for {cart.user.email}: {e}")

    logger.info(f"Abandoned cart emails sent: {sent}")
    return {"sent": sent}


@shared_task(name="apps.notifications.tasks.update_product_total_sold")
def update_product_total_sold(order_id: str):
    """
    After payment is confirmed, increment Product.total_sold
    for each item in the order.
    """
    try:
        from apps.orders.models import Order
        from apps.products.models import Product

        order = Order.objects.prefetch_related("items__product").get(id=order_id)
        for item in order.items.all():
            if item.product:
                Product.objects.filter(pk=item.product.pk).update(
                    total_sold=item.product.total_sold + item.quantity
                )

        logger.info(f"Updated total_sold for order {order.order_number}")

    except Exception as exc:
        logger.error(f"update_product_total_sold failed for order {order_id}: {exc}")