from django.contrib import admin
from .models import Review, ReviewHelpful


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        "product", "user", "rating", "is_verified",
        "is_approved", "helpful_count", "created_at",
    ]
    list_filter = ["rating", "is_verified", "is_approved", "created_at"]
    search_fields = ["product__name", "user__email", "title", "body"]
    readonly_fields = ["id", "helpful_count", "unhelpful_count", "created_at", "updated_at"]
    date_hierarchy = "created_at"

    actions = ["approve_reviews", "unapprove_reviews"]

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "Approve selected reviews"

    def unapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)
    unapprove_reviews.short_description = "Hide selected reviews"