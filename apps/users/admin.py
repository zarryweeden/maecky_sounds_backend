from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Address


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    readonly_fields = ["created_at", "updated_at"]
    fields = ["label", "full_name", "city", "county", "is_default", "created_at"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "full_name", "is_active", "is_staff", "email_verified", "date_joined"]
    list_filter = ["is_active", "is_staff", "email_verified", "newsletter_subscribed"]
    search_fields = ["email", "full_name", "phone"]
    ordering = ["-date_joined"]
    readonly_fields = ["id", "date_joined", "last_login"]
    date_hierarchy = "date_joined"
    inlines = [AddressInline]

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (_("Personal Info"), {"fields": ("full_name", "phone", "avatar")}),
        (_("Account Status"), {"fields": ("is_active", "is_staff", "is_superuser", "email_verified")}),
        (_("Marketing"), {"fields": ("newsletter_subscribed", "marketing_emails")}),
        (_("Permissions"), {"fields": ("groups", "user_permissions")}),
        (_("Timestamps"), {"fields": ("date_joined", "last_login")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "password1", "password2", "is_staff"),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["user", "label", "full_name", "city", "county", "is_default"]
    list_filter = ["is_default", "county"]
    search_fields = ["user__email", "full_name", "city"]
    readonly_fields = ["id", "created_at", "updated_at"]