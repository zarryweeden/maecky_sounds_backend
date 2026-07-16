"""
Stripe payment integration.

Environment variables required:
    STRIPE_SECRET_KEY
    STRIPE_WEBHOOK_SECRET
    STRIPE_PUBLIC_KEY
"""

import logging
import stripe
from django.conf import settings

logger = logging.getLogger(__name__)


def get_stripe():
    """Return configured Stripe client."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def create_payment_intent(amount: int, order_number: str, currency: str = "kes") -> dict:
    """
    Create a Stripe PaymentIntent for the given amount.

    Args:
        amount:       Amount in KES (integer)
        order_number: Used as metadata reference
        currency:     Stripe currency code (default: kes)

    Returns:
        {
            "payment_intent_id": str,
            "client_secret": str,
            "amount": int,
            "currency": str,
        }
    """
    s = get_stripe()
    try:
        intent = s.PaymentIntent.create(
            amount=amount * 100,  # Stripe uses smallest currency unit (cents/paise)
            currency=currency,
            metadata={
                "order_number": order_number,
                "store": "maecky_sounds",
            },
            description=f"Maecky Sounds Order {order_number}",
            automatic_payment_methods={"enabled": True},
        )
        logger.info(f"PaymentIntent created for order {order_number}: {intent.id}")
        return {
            "payment_intent_id": intent.id,
            "client_secret": intent.client_secret,
            "amount": amount,
            "currency": currency.upper(),
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe PaymentIntent creation failed: {e}")
        raise


def retrieve_payment_intent(payment_intent_id: str) -> dict:
    """Retrieve a PaymentIntent from Stripe."""
    s = get_stripe()
    try:
        intent = s.PaymentIntent.retrieve(payment_intent_id)
        return {
            "id": intent.id,
            "status": intent.status,
            "amount": intent.amount // 100,
            "currency": intent.currency.upper(),
        }
    except stripe.error.StripeError as e:
        logger.error(f"Stripe retrieve PaymentIntent failed: {e}")
        raise


def construct_webhook_event(payload: bytes, sig_header: str):
    """
    Verify and construct a Stripe webhook event.
    Raises stripe.error.SignatureVerificationError if invalid.
    """
    s = get_stripe()
    return s.Webhook.construct_event(
        payload,
        sig_header,
        settings.STRIPE_WEBHOOK_SECRET,
    )


def create_refund(payment_intent_id: str, amount: int = None) -> dict:
    """
    Create a full or partial refund for a PaymentIntent.

    Args:
        payment_intent_id: Stripe PaymentIntent ID
        amount:            Amount to refund in KES (None = full refund)
    """
    s = get_stripe()
    kwargs = {"payment_intent": payment_intent_id}
    if amount is not None:
        kwargs["amount"] = amount * 100

    try:
        refund = s.Refund.create(**kwargs)
        logger.info(f"Stripe refund created: {refund.id}")
        return {"refund_id": refund.id, "status": refund.status}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe refund failed: {e}")
        raise