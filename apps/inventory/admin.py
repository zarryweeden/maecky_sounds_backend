from django.contrib import admin
from django.utils.html import format_html
from .models import Inventory, InventoryLog


class InventoryLogInline(admin.TabularInline):
    model = InventoryLog
    extra = 0
    readonly_fields = [
        "reason", "delta", "quantity_after",
        "reference", "note", "created_by", "created_at",
    ]
    can_delete = False
    max_num = 20
    ordering = ["-created_at"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = [
        "product", "quantity", "reserved", "available_display",
        "low_stock_threshold", "stock_status", "track_inventory",
        "allow_backorder", "updated_at",
    ]
    list_filter = ["track_inventory", "allow_backorder"]
    search_fields = ["product__name", "product__sku"]
    readonly_fields = ["id", "updated_at"]
    inlines = [InventoryLogInline]

    def available_display(self, obj):
        return obj.available
    available_display.short_description = "Available"

    def stock_status(self, obj):
        if not obj.is_in_stock:
            return format_html(
                '<span style="color:red;font-weight:bold;">{}</span>',
                'Out of Stock'
            )

        if obj.is_low_stock:
            return format_html(
                '<span style="color:orange;font-weight:bold;">{}</span>',
                'Low Stock'
            )

        return format_html(
            '<span style="color:green;">{}</span>',
            'In Stock'
        )

    stock_status.short_description = "Status"
    def send_low_stock_alerts(self, request, queryset):
        from apps.notifications.tasks import send_low_stock_alert
        count = 0
        for inv in queryset:
            if inv.is_low_stock:
                send_low_stock_alert.delay(str(inv.product.id))
                count += 1
        self.message_user(request, f"Sent low stock alerts for {count} products.")
    send_low_stock_alerts.short_description = "Send low stock alert emails"

    actions = ["send_low_stock_alerts"]


@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = [
        "inventory", "reason", "delta", "quantity_after",
        "reference", "created_by", "created_at",
    ]
    list_filter = ["reason", "created_at"]
    search_fields = [
        "inventory__product__name",
        "inventory__product__sku",
        "reference",
    ]
    readonly_fields = [
        "id", "inventory", "reason", "delta", "quantity_after",
        "reference", "note", "created_by", "created_at",
    ]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False