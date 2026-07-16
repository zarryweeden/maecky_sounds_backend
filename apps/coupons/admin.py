from django.contrib import admin
from django.utils.html import format_html
from .models import Coupon, CouponUsage


class CouponUsageInline(admin.TabularInline):
    model = CouponUsage
    extra = 0
    readonly_fields = ["user", "order", "discount", "used_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = [
        "code", "discount_type", "discount_value", "is_active",
        "used_count", "usage_limit", "valid_from", "valid_until",
        "minimum_order",
    ]
    list_filter = ["is_active", "discount_type", "valid_from"]
    search_fields = ["code", "description"]
    readonly_fields = ["id", "used_count", "created_at", "updated_at"]
    filter_horizontal = ["applicable_categories", "applicable_products"]
    inlines = [CouponUsageInline]

    fieldsets = (
        ("Coupon Code", {
            "fields": ("id", "code", "description", "is_active"),
        }),
        ("Discount", {
            "fields": ("discount_type", "discount_value", "maximum_discount"),
        }),
        ("Restrictions", {
            "fields": (
                "minimum_order", "usage_limit", "usage_per_user",
                "used_count", "valid_from", "valid_until",
            ),
        }),
        ("Applicable To (optional)", {
            "fields": ("applicable_categories", "applicable_products"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ["coupon", "user", "order", "discount", "used_at"]
    list_filter = ["used_at"]
    search_fields = ["coupon__code", "user__email", "order__order_number"]
    readonly_fields = ["id", "coupon", "user", "order", "discount", "used_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False