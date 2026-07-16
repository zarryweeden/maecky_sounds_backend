import uuid
from django.db import models
from django.utils import timezone


class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage Off"
        FIXED = "fixed", "Fixed Amount Off (KES)"
        FREE_SHIP = "free_ship", "Free Shipping"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.CharField(max_length=255, blank=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.PositiveIntegerField(
        help_text="Percentage (0–100) or KES amount depending on discount_type."
    )

    # Restrictions
    minimum_order = models.PositiveIntegerField(
        default=0,
        help_text="Minimum cart subtotal in KES to use this coupon.",
    )
    maximum_discount = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Maximum discount cap in KES (for percentage discounts).",
    )
    usage_limit = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Maximum total uses. Null = unlimited.",
    )
    usage_per_user = models.PositiveIntegerField(
        default=1,
        help_text="Max uses per individual user.",
    )
    used_count = models.PositiveIntegerField(default=0)

    # Validity window
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    # Optional product/category constraints
    applicable_categories = models.ManyToManyField(
        "products.Category", blank=True,
        related_name="coupons",
    )
    applicable_products = models.ManyToManyField(
        "products.Product", blank=True,
        related_name="coupons",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "coupons"
        ordering = ["-created_at"]
        verbose_name = "Coupon"
        verbose_name_plural = "Coupons"

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()})"

    def is_valid(self, user, cart) -> tuple:
        """
        Check if this coupon is valid for the given user and cart.

        Returns:
            (True, "") if valid
            (False, "Reason message") if not valid
        """
        now = timezone.now()

        if not self.is_active:
            return False, "This coupon is no longer active."

        if now < self.valid_from:
            return False, "This coupon is not yet valid."

        if self.valid_until and now > self.valid_until:
            return False, "This coupon has expired."

        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, "This coupon has reached its usage limit."

        if cart.subtotal < self.minimum_order:
            from apps.payments.mpesa import format_phone  # avoid circular
            return (
                False,
                f"This coupon requires a minimum order of KES {self.minimum_order:,}.",
            )

        if user and user.is_authenticated:
            user_usage = CouponUsage.objects.filter(
                coupon=self, user=user
            ).count()
            if user_usage >= self.usage_per_user:
                return False, "You have already used this coupon the maximum number of times."

        return True, ""

    def calculate_discount(self, cart) -> int:
        """
        Calculate the discount amount in KES for the given cart.
        Returns an integer KES amount.
        """
        subtotal = cart.subtotal

        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = int((self.discount_value / 100) * subtotal)
            if self.maximum_discount:
                discount = min(discount, self.maximum_discount)
            return discount

        if self.discount_type == self.DiscountType.FIXED:
            return min(self.discount_value, subtotal)

        if self.discount_type == self.DiscountType.FREE_SHIP:
            return 0  # Shipping is zeroed separately

        return 0


class CouponUsage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="usages")
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="coupon_usages",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="coupon_usages",
    )
    discount = models.PositiveIntegerField(help_text="Actual KES discount applied.")
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "coupon_usages"
        ordering = ["-used_at"]
        verbose_name = "Coupon Usage"
        verbose_name_plural = "Coupon Usages"

    def __str__(self):
        return f"{self.coupon.code} used by {self.user.email}"