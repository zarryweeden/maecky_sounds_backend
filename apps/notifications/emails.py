"""
Email helper functions.
All email sending goes through these helpers so templates and
subjects are defined in one place.
"""
import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_email(
    subject: str,
    template_name: str,
    context: dict,
    recipient_email: str,
    fail_silently: bool = True,
) -> bool:
    """
    Render an HTML email template and send it.

    Args:
        subject:         Email subject line
        template_name:   Template path relative to templates/emails/
        context:         Template context dict
        recipient_email: Recipient's email address
        fail_silently:   If True, log errors instead of raising

    Returns:
        True if sent successfully, False otherwise
    """
    context.setdefault("frontend_url", settings.FRONTEND_URL)
    context.setdefault("store_name", "Maecky Sounds")
    context.setdefault("support_email", "hello@maeckysounds.co.ke")
    context.setdefault("store_phone", "+254 700 123 456")

    try:
        html_content = render_to_string(f"emails/{template_name}", context)
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        logger.info(f"Email sent: '{subject}' → {recipient_email}")
        return True

    except Exception as e:
        logger.error(f"Email send failed: '{subject}' → {recipient_email}: {e}")
        if not fail_silently:
            raise
        return False


def send_order_confirmation(order) -> bool:
    return send_email(
        subject=f"Order Confirmed — {order.order_number} | Maecky Sounds",
        template_name="order_confirmation.html",
        context={
            "order": order,
            "items": order.items.all(),
            "order_url": f"{settings.FRONTEND_URL}/account/orders/{order.order_number}",
        },
        recipient_email=order.customer_email,
    )


def send_shipping_update(order, tracking_number: str) -> bool:
    return send_email(
        subject=f"Your Order Has Shipped — {order.order_number} | Maecky Sounds",
        template_name="shipping_update.html",
        context={
            "order": order,
            "tracking_number": tracking_number,
            "order_url": f"{settings.FRONTEND_URL}/account/orders/{order.order_number}",
        },
        recipient_email=order.customer_email,
    )


def send_welcome(user) -> bool:
    return send_email(
        subject="Welcome to Maecky Sounds 🎸",
        template_name="welcome.html",
        context={
            "user": user,
            "shop_url": f"{settings.FRONTEND_URL}/category/guitars",
        },
        recipient_email=user.email,
    )


def send_password_reset(user, reset_url: str) -> bool:
    return send_email(
        subject="Reset Your Maecky Sounds Password",
        template_name="password_reset.html",
        context={
            "user": user,
            "reset_url": reset_url,
        },
        recipient_email=user.email,
    )


def send_low_stock_alert_email(product, admin_email: str) -> bool:
    try:
        stock = product.inventory.available
    except Exception:
        stock = 0

    return send_email(
        subject=f"⚠ Low Stock Alert: {product.name}",
        template_name="low_stock_alert.html",
        context={
            "product": product,
            "stock": stock,
            "admin_url": f"{settings.FRONTEND_URL.replace('3000', '8000')}/store-management/",
        },
        recipient_email=admin_email,
    )


def send_abandoned_cart_email(user, cart) -> bool:
    return send_email(
        subject="You left something behind 🎸 — Maecky Sounds",
        template_name="abandoned_cart.html",
        context={
            "user": user,
            "cart": cart,
            "items": cart.items.select_related("product").all(),
            "cart_url": f"{settings.FRONTEND_URL}/cart",
        },
        recipient_email=user.email,
    )