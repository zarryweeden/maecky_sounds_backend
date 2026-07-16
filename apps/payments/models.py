import uuid
from django.db import models
from django.conf import settings


class Payment(models.Model):
    class Method(models.TextChoices):
        MPESA = "mpesa", "M-Pesa"
        CARD = "card", "Credit/Debit Card"
        PAYPAL = "paypal", "PayPal"
        BANK = "bank", "Bank Transfer"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    method = models.CharField(max_length=20, choices=Method.choices, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    amount = models.PositiveIntegerField(help_text="Amount in KES")
    currency = models.CharField(max_length=3, default="KES")

    # Provider references
    transaction_id = models.CharField(
        max_length=200, blank=True, db_index=True,
        help_text="Our internal transaction reference.",
    )
    provider_ref = models.CharField(
        max_length=200, blank=True,
        help_text="Provider's reference (e.g. M-Pesa CheckoutRequestID, Stripe PaymentIntent ID).",
    )
    provider_response = models.JSONField(
        default=dict,
        help_text="Raw callback/webhook data from the payment provider.",
    )

    # M-Pesa specific
    mpesa_phone = models.CharField(max_length=20, blank=True)
    mpesa_receipt = models.CharField(
        max_length=100, blank=True,
        help_text="M-Pesa transaction receipt number from Safaricom.",
    )

    # Stripe specific
    stripe_payment_intent = models.CharField(max_length=200, blank=True)
    stripe_client_secret = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payments"
        ordering = ["-created_at"]
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["method", "status"]),
        ]

    def __str__(self):
        return f"{self.order.order_number} — {self.method} — {self.status} — KES {self.amount:,}"

    def mark_completed(self, transaction_id="", provider_response=None):
        from django.utils import timezone
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        if transaction_id:
            self.transaction_id = transaction_id
        if provider_response:
            self.provider_response = provider_response
        self.save()

    def mark_failed(self, provider_response=None):
        self.status = self.Status.FAILED
        if provider_response:
            self.provider_response = provider_response
        self.save()