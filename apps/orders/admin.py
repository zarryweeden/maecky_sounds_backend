import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils import timezone
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory


def export_orders_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="orders.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Order Number", "Customer Email", "Customer Name",
        "Status", "Total (KES)", "Delivery Method",
        "City", "Created At",
    ])
    for o in queryset:
        addr = o.shipping_address or {}
        writer.writerow([
            o.order_number, o.customer_email, o.customer_name,
            o.get_status_display(), o.total,
            o.get_delivery_method_display(),
            addr.get("city", ""),
            o.created_at.strftime("%Y-%m-%d %H:%M"),
        ])
    return response


export_orders_csv.short_description = "Export selected orders as CSV"


def mark_as_shipped(modeladmin, request, queryset):
    for order in queryset.filter(status=Order.Status.CONFIRMED):
        order.transition_to(
            Order.Status.SHIPPED,
            note="Bulk marked as shipped via admin.",
            changed_by=request.user,
        )


mark_as_shipped.short_description = "Mark selected orders as Shipped"


def mark_as_delivered(modeladmin, request, queryset):
    for order in queryset.filter(status=Order.Status.SHIPPED):
        order.transition_to(
            Order.Status.DELIVERED,
            note="Bulk marked as delivered via admin.",
            changed_by=request.user,
        )


mark_as_delivered.short_description = "Mark selected orders as Delivered"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = [
        "product", "product_name", "product_sku",
        "variant_name", "quantity", "unit_price", "total_price",
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ["status", "note", "changed_by", "created_at"]
    can_delete = False
    ordering = ["-created_at"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number", "customer_email", "customer_name",
        "status_badge", "total_display", "delivery_method",
        "created_at", "items_count",
    ]
    list_filter = ["status", "delivery_method", "created_at"]
    search_fields = [
        "order_number", "customer_email",
        "customer_name", "customer_phone",
    ]
    readonly_fields = [
        "id", "order_number", "subtotal", "discount_amount",
        "shipping_cost", "total", "created_at", "updated_at",
        "confirmed_at", "shipped_at", "delivered_at", "cancelled_at",
    ]
    date_hierarchy = "created_at"
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    actions = [export_orders_csv, mark_as_shipped, mark_as_delivered]
    list_per_page = 25

    fieldsets = (
        ("Order Info", {
            "fields": ("id", "order_number", "user", "status"),
        }),
        ("Customer", {
            "fields": ("customer_email", "customer_name", "customer_phone"),
        }),
        ("Financials (KES)", {
            "fields": ("subtotal", "discount_amount", "shipping_cost", "total", "coupon_code"),
        }),
        ("Delivery", {
            "fields": (
                "delivery_method", "shipping_address",
                "estimated_delivery", "tracking_number",
            ),
        }),
        ("Notes", {
            "fields": ("customer_notes", "admin_notes"),
        }),
        ("Timestamps", {
            "fields": (
                "created_at", "updated_at", "confirmed_at",
                "shipped_at", "delivered_at", "cancelled_at",
            ),
            "classes": ("collapse",),
        }),
    )

    def status_badge(self, obj):
        colours = {
            "pending": "orange",
            "confirmed": "blue",
            "processing": "purple",
            "shipped": "teal",
            "delivered": "green",
            "cancelled": "red",
            "refunded": "gray",
        }
        colour = colours.get(obj.status, "gray")
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            colour,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def total_display(self, obj):
        return f"KES {obj.total:,}"
    total_display.short_description = "Total"

    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = "Items"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["__str__", "user", "is_active", "total_items_display", "updated_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["user__email", "session_key"]
    readonly_fields = ["id", "created_at", "updated_at"]

    def total_items_display(self, obj):
        return obj.total_items
    total_items_display.short_description = "Items"