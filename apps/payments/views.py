import json
import logging

from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from .models import Payment
from .serializers import (
    MpesaInitiateSerializer,
    StripeInitiateSerializer,
    StripeConfirmSerializer,
    PaymentSerializer,
)

logger = logging.getLogger(__name__)


def _confirm_order_payment(order, payment):
    """
    Called after any payment method confirms success.
    - Transitions order to CONFIRMED
    - Confirms inventory deduction
    - Updates product total_sold
    - Fires confirmation email task
    """
    from apps.notifications.tasks import send_order_confirmation_email
    from apps.notifications.tasks import update_product_total_sold

    order.transition_to(
        Order.Status.CONFIRMED,
        note=f"Payment confirmed via {payment.get_method_display()}. "
             f"Transaction: {payment.transaction_id or payment.mpesa_receipt}",
    )

    # Confirm inventory deductions
    for item in order.items.select_related("product__inventory"):
        if item.product:
            try:
                item.product.inventory.confirm_sale(
                    quantity=item.quantity,
                    reference=order.order_number,
                    note=f"Sale confirmed — payment {payment.id}",
                )
                # Increment total_sold
                from apps.products.models import Product
                Product.objects.filter(pk=item.product.pk).update(
                    total_sold=item.product.total_sold + item.quantity
                )
            except Exception as e:
                logger.warning(
                    f"Could not confirm inventory for {item.product_sku}: {e}"
                )

    send_order_confirmation_email.delay(str(order.id))


# ── M-Pesa Views ──────────────────────────────────────────────────────────────

class MpesaInitiateView(APIView):
    """Initiate an M-Pesa STK Push payment for an order."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MpesaInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data["order_id"]
        phone = serializer.validated_data["phone"]

        # Validate order belongs to user
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"status": "error", "message": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.status not in [Order.Status.PENDING]:
            return Response(
                {
                    "status": "error",
                    "message": f"Cannot initiate payment for an order with status: {order.get_status_display()}.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create pending payment record
        payment = Payment.objects.create(
            order=order,
            method=Payment.Method.MPESA,
            amount=order.total,
            mpesa_phone=phone,
        )

        try:
            from .mpesa import initiate_stk_push
            response_data = initiate_stk_push(
                phone=phone,
                amount=order.total,
                order_number=order.order_number,
            )
        except Exception as e:
            payment.mark_failed({"error": str(e)})
            logger.error(f"M-Pesa STK Push error for order {order.order_number}: {e}")
            return Response(
                {
                    "status": "error",
                    "message": "Failed to initiate M-Pesa payment. Please try again.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Store the CheckoutRequestID so we can match the callback
        checkout_request_id = response_data.get("CheckoutRequestID", "")
        payment.provider_ref = checkout_request_id
        payment.provider_response = response_data
        payment.save(update_fields=["provider_ref", "provider_response"])

        return Response(
            {
                "status": "success",
                "message": "M-Pesa payment request sent. Please check your phone and enter your PIN.",
                "checkout_request_id": checkout_request_id,
                "payment_id": str(payment.id),
                "amount": order.total,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class MpesaCallbackView(APIView):
    """
    Webhook endpoint for Safaricom Daraja callbacks.
    This URL must be publicly accessible and whitelisted with Safaricom.
    CSRF exempt — Safaricom does not send CSRF tokens.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request):
        try:
            data = request.data
        except Exception:
            logger.warning("M-Pesa callback: could not parse request body.")
            return Response({"ResultCode": 1, "ResultDesc": "Failed"})

        from .mpesa import verify_callback, parse_successful_callback

        if not verify_callback(data):
            logger.warning(f"M-Pesa callback validation failed: {data}")
            return Response({"ResultCode": 1, "ResultDesc": "Validation Failed"})

        parsed = parse_successful_callback(data)
        checkout_request_id = parsed["checkout_request_id"]
        result_code = parsed["result_code"]

        # Find the matching payment
        try:
            payment = Payment.objects.select_related("order__items__product__inventory").get(
                provider_ref=checkout_request_id,
                method=Payment.Method.MPESA,
            )
        except Payment.DoesNotExist:
            logger.warning(
                f"M-Pesa callback: no payment found for CheckoutRequestID {checkout_request_id}"
            )
            return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

        if payment.status == Payment.Status.COMPLETED:
            # Already processed — idempotent response
            return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

        if result_code == 0:
            # Payment successful
            payment.mpesa_receipt = parsed["receipt"]
            payment.mark_completed(
                transaction_id=parsed["receipt"],
                provider_response=data,
            )
            logger.info(
                f"M-Pesa payment confirmed: {parsed['receipt']} for order {payment.order.order_number}"
            )
            _confirm_order_payment(payment.order, payment)
        else:
            # Payment failed or cancelled by user
            payment.mark_failed(provider_response=data)
            logger.info(
                f"M-Pesa payment failed for order {payment.order.order_number}: "
                f"{parsed['result_desc']}"
            )

        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


class MpesaStatusView(APIView):
    """Poll Safaricom directly for the status of a pending STK Push."""
    permission_classes = [IsAuthenticated]

    def get(self, request, checkout_request_id):
        try:
            from .mpesa import query_stk_push
            result = query_stk_push(checkout_request_id)
        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Also return our local payment record status
        payment = Payment.objects.filter(
            provider_ref=checkout_request_id,
            method=Payment.Method.MPESA,
        ).first()

        return Response(
            {
                "status": "success",
                "daraja_response": result,
                "payment_status": payment.status if payment else None,
                "payment_id": str(payment.id) if payment else None,
            }
        )


# ── Stripe Views ──────────────────────────────────────────────────────────────

class StripeInitiateView(APIView):
    """Create a Stripe PaymentIntent and return the client_secret to the frontend."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StripeInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = Order.objects.get(
                id=serializer.validated_data["order_id"],
                user=request.user,
            )
        except Order.DoesNotExist:
            return Response(
                {"status": "error", "message": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.status not in [Order.Status.PENDING]:
            return Response(
                {
                    "status": "error",
                    "message": f"Cannot initiate payment: order is {order.get_status_display()}.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from .stripe_client import create_payment_intent
            intent_data = create_payment_intent(
                amount=order.total,
                order_number=order.order_number,
            )
        except Exception as e:
            logger.error(f"Stripe initiate failed for order {order.order_number}: {e}")
            return Response(
                {"status": "error", "message": "Failed to initiate card payment. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Create payment record
        payment = Payment.objects.create(
            order=order,
            method=Payment.Method.CARD,
            amount=order.total,
            provider_ref=intent_data["payment_intent_id"],
            stripe_payment_intent=intent_data["payment_intent_id"],
            stripe_client_secret=intent_data["client_secret"],
            provider_response=intent_data,
        )

        return Response(
            {
                "status": "success",
                "payment_id": str(payment.id),
                "client_secret": intent_data["client_secret"],
                "payment_intent_id": intent_data["payment_intent_id"],
                "amount": order.total,
                "publishable_key": getattr(settings, "STRIPE_PUBLIC_KEY", ""),
            }
        )


class StripeConfirmView(APIView):
    """
    Called by the frontend after Stripe.js confirms the payment.
    Verifies the PaymentIntent status with Stripe and updates our records.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = StripeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment_intent_id = serializer.validated_data["payment_intent_id"]
        order_id = serializer.validated_data["order_id"]

        try:
            payment = Payment.objects.select_related(
                "order__items__product__inventory"
            ).get(
                stripe_payment_intent=payment_intent_id,
                order__id=order_id,
                order__user=request.user,
            )
        except Payment.DoesNotExist:
            return Response(
                {"status": "error", "message": "Payment record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if payment.status == Payment.Status.COMPLETED:
            return Response(
                {
                    "status": "success",
                    "message": "Payment already confirmed.",
                    "order_number": payment.order.order_number,
                }
            )

        # Verify with Stripe
        try:
            from .stripe_client import retrieve_payment_intent
            intent = retrieve_payment_intent(payment_intent_id)
        except Exception as e:
            logger.error(f"Stripe confirm failed: {e}")
            return Response(
                {"status": "error", "message": "Could not verify payment with Stripe."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if intent["status"] == "succeeded":
            payment.mark_completed(
                transaction_id=payment_intent_id,
                provider_response=intent,
            )
            _confirm_order_payment(payment.order, payment)
            return Response(
                {
                    "status": "success",
                    "message": "Payment confirmed! Your order is being processed.",
                    "order_number": payment.order.order_number,
                }
            )

        # Payment not yet succeeded
        payment.mark_failed(provider_response=intent)
        return Response(
            {
                "status": "error",
                "message": f"Payment was not completed. Status: {intent['status']}.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    """
    Stripe webhook endpoint.
    Verifies the Stripe-Signature header and processes payment events.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        try:
            from .stripe_client import construct_webhook_event
            event = construct_webhook_event(payload, sig_header)
        except Exception as e:
            logger.warning(f"Stripe webhook signature verification failed: {e}")
            return Response(
                {"error": "Invalid signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event_type = event["type"]
        logger.info(f"Stripe webhook received: {event_type}")

        if event_type == "payment_intent.succeeded":
            intent = event["data"]["object"]
            payment_intent_id = intent["id"]

            try:
                payment = Payment.objects.select_related(
                    "order__items__product__inventory"
                ).get(stripe_payment_intent=payment_intent_id)

                if payment.status != Payment.Status.COMPLETED:
                    payment.mark_completed(
                        transaction_id=payment_intent_id,
                        provider_response=dict(intent),
                    )
                    _confirm_order_payment(payment.order, payment)
                    logger.info(
                        f"Stripe webhook: payment confirmed for order "
                        f"{payment.order.order_number}"
                    )
            except Payment.DoesNotExist:
                logger.warning(
                    f"Stripe webhook: no payment found for PaymentIntent {payment_intent_id}"
                )

        elif event_type == "payment_intent.payment_failed":
            intent = event["data"]["object"]
            payment_intent_id = intent["id"]
            try:
                payment = Payment.objects.get(stripe_payment_intent=payment_intent_id)
                if payment.status == Payment.Status.PENDING:
                    payment.mark_failed(provider_response=dict(intent))
                    logger.info(
                        f"Stripe webhook: payment failed for order "
                        f"{payment.order.order_number}"
                    )
            except Payment.DoesNotExist:
                pass

        elif event_type == "charge.refunded":
            charge = event["data"]["object"]
            payment_intent_id = charge.get("payment_intent")
            if payment_intent_id:
                try:
                    payment = Payment.objects.get(stripe_payment_intent=payment_intent_id)
                    payment.status = Payment.Status.REFUNDED
                    payment.save(update_fields=["status"])
                    payment.order.transition_to(Order.Status.REFUNDED, note="Stripe refund processed.")
                except Payment.DoesNotExist:
                    pass

        # Always return 200 to Stripe so it doesn't retry
        return Response({"received": True})


# ── Payment Status View ───────────────────────────────────────────────────────

class PaymentStatusView(APIView):
    """Poll our local payment status for a given payment ID."""
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):
        try:
            payment = Payment.objects.select_related("order").get(
                id=payment_id,
                order__user=request.user,
            )
        except Payment.DoesNotExist:
            return Response(
                {"status": "error", "message": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "status": "success",
                "payment": PaymentSerializer(payment).data,
            }
        )