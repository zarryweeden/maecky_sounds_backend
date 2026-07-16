import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
from .models import Category, Brand, Product, ProductImage, ProductSpecification, ProductVariant, Tag


def export_products_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="products.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "SKU", "Name", "Brand", "Category", "Price (KES)",
        "Sale Price (KES)", "Condition", "Is Active", "Is Featured",
        "Average Rating", "Review Count", "Total Sold",
    ])
    for p in queryset.select_related("brand", "category"):
        writer.writerow([
            p.sku, p.name, p.brand.name, p.category.name,
            p.price, p.sale_price or "", p.condition,
            p.is_active, p.is_featured,
            p.average_rating, p.review_count, p.total_sold,
        ])
    return response


export_products_csv.short_description = "Export selected products as CSV"


def recalculate_ratings(modeladmin, request, queryset):
    from django.db.models import Avg, Count
    from apps.reviews.models import Review
    for product in queryset:
        agg = Review.objects.filter(product=product, is_approved=True).aggregate(
            avg=Avg("rating"), count=Count("id")
        )
        product.average_rating = agg["avg"] or 0
        product.review_count = agg["count"] or 0
        product.save(update_fields=["average_rating", "review_count"])


recalculate_ratings.short_description = "Recalculate ratings for selected products"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ["preview", "created_at"]
    fields = ["image", "preview", "alt_text", "is_primary", "sort_order", "created_at"]

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" height="60" />', obj.image.url)
        return "—"
    preview.short_description = "Preview"


class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 2
    fields = ["key", "value", "sort_order"]


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ["name", "value", "sku_suffix", "price_delta", "is_active"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name", "sku", "brand", "category", "price", "sale_price",
        "is_active", "is_featured", "is_new", "is_hot",
        "average_rating", "review_count", "total_sold", "stock_status",
    ]
    list_filter = [
        "is_active", "is_featured", "is_new", "is_hot",
        "condition", "brand", "category",
    ]
    search_fields = ["name", "sku", "brand__name", "category__name"]
    ordering = ["-created_at"]
    readonly_fields = [
        "id", "slug", "average_rating", "review_count",
        "total_sold", "view_count", "created_at", "updated_at",
    ]
    date_hierarchy = "created_at"
    filter_horizontal = ["tags"]
    inlines = [ProductImageInline, ProductSpecificationInline, ProductVariantInline]
    actions = [export_products_csv, recalculate_ratings]
    list_per_page = 25

    fieldsets = (
        ("Basic Info", {
            "fields": ("id", "sku", "name", "slug", "brand", "category", "condition", "tags", "weight"),
        }),
        ("Pricing (KES)", {
            "fields": ("price", "sale_price"),
            "description": "All prices in Kenya Shillings (KES). No decimals.",
        }),
        ("Content", {
            "fields": ("short_description", "description"),
            "classes": ("wide",),
        }),
        ("Visibility Flags", {
            "fields": ("is_active", "is_featured", "is_new", "is_hot"),
        }),
        ("Stats (auto-computed)", {
            "fields": ("average_rating", "review_count", "total_sold", "view_count"),
            "classes": ("collapse",),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def stock_status(self, obj):
        try:
            inv = obj.inventory
            if inv.is_in_stock:
                color = "green" if not inv.is_low_stock else "orange"
                label = f"{inv.available} units" if not inv.is_low_stock else f"Low ({inv.available})"
            else:
                color, label = "red", "Out of Stock"
            return format_html('<span style="color:{}">{}</span>', color, label)
        except Exception:
            return format_html('<span style="color:gray">No inventory</span>')

    stock_status.short_description = "Stock"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "parent", "is_active", "sort_order", "created_at"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["sort_order", "name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "sort_order", "website"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["sort_order", "name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "created_at"]
    prepopulated_fields = {"slug": ("name",)}