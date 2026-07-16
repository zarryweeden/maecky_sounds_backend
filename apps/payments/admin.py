from django.contrib import admin
from django.utils.html import format_html
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "order", "method", "status_badge", "amount_display",
        "transaction_id", "mpesa_receipt", "created_at", "completed_at",
    ]
    list_filter = ["method", "status", "created_at"]
    search_fields = [
        "order__order_number", "transaction_id",
        "mpesa_receipt", "mpesa_phone", "provider_ref",
    ]
    readonly_fields = [
        "id", "order", "method", "status", "amount", "currency",
        "transaction_id", "provider_ref", "provider_response",
        "mpesa_phone", "mpesa_receipt",
        "stripe_payment_intent",
        "created_at", "updated_at", "completed_at",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    def amount_display(self, obj):
        return f"KES {obj.amount:,}"
    amount_display.short_description = "Amount"

    def status_badge(self, obj):
        colours = {
            "pending": "orange",
            "completed": "green",
            "failed": "red",
            "refunded": "gray",
            "cancelled": "darkgray",
        }
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            colours.get(obj.status, "black"),
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False