from django.urls import path
from .views import (
    MpesaInitiateView,
    MpesaCallbackView,
    MpesaStatusView,
    StripeInitiateView,
    StripeConfirmView,
    StripeWebhookView,
    PaymentStatusView,
)

urlpatterns = [
    # M-Pesa
    path("mpesa/initiate/", MpesaInitiateView.as_view(), name="mpesa-initiate"),
    path("mpesa/callback/", MpesaCallbackView.as_view(), name="mpesa-callback"),
    path("mpesa/status/<str:checkout_request_id>/", MpesaStatusView.as_view(), name="mpesa-status"),
    # Stripe
    path("stripe/initiate/", StripeInitiateView.as_view(), name="stripe-initiate"),
    path("stripe/confirm/", StripeConfirmView.as_view(), name="stripe-confirm"),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
    # Generic
    path("<uuid:payment_id>/status/", PaymentStatusView.as_view(), name="payment-status"),
]