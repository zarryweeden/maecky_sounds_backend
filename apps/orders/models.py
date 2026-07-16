import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_order_number():
    """Generate MS-YYYY-XXXXXX format order numbers."""
    year = timezone.now().year
    last = (
        Order.objects.filter(created_at__year=year)
        .order_by("-created_at")
        .first()
    )
    if last:
        try:
            seq = int(last.order_number.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"MS-{year}-{seq:06d}"


class Cart(models.Model):
    """
    Persistent cart — works for both guests (session_key)
    and authenticated users (user FK).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="carts",
    )
    session_key = models.CharField(
        max_length=200, blank=True, db_index=True,
        help_text="Used to identify guest carts.",
    )
    coupon = models.ForeignKey(
        "coupons.Coupon",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="carts",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "carts"
        ordering = ["-updated_at"]
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

    def __str__(self):
        if self.user:
            return f"Cart — {self.user.email}"
        return f"Guest Cart — {self.session_key[:16]}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.all())

    @property
    def discount_amount(self):
        if not self.coupon:
            return 0
        try:
            return self.coupon.calculate_discount(self)
        except Exception:
            return 0

    @property
    def shipping_cost(self):
        from apps.orders.utils import calculate_shipping
        return calculate_shipping(self.subtotal, "standard")

    @property
    def total(self):
        return max(0, self.subtotal - self.discount_amount)

    def merge_with(self, other_cart):
        """
        Merge another cart's items into this cart.
        Used when a guest logs in and their session cart
        needs to be merged with their user cart.
        """
        for item in other_cart.items.select_related("product", "variant"):
            existing = self.items.filter(
                product=item.product, variant=item.variant
            ).first()
            if existing:
                existing.quantity = min(
                    existing.quantity + item.quantity,
                    item.product.inventory.available if hasattr(item.product, "inventory") else 999,
                )
                existing.save(update_fields=["quantity"])
            else:
                item.pk = None
                item.id = uuid.uuid4()
                item.cart = self
                item.save()

        other_cart.is_active = False
        other_cart.save(update_fields=["is_active"])


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    variant = models.ForeignKey(
        "products.ProductVariant",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.PositiveIntegerField(
        help_text="Price at the time the item was added to cart (KES)."
    )
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cart_items"
        ordering = ["added_at"]
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        unique_together = [["cart", "product", "variant"]]

    def __str__(self):
        return f"{self.quantity}× {self.product.name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def save(self, *args, **kwargs):
        # Always snapshot the current effective price when adding to cart
        if not self.unit_price:
            if self.variant:
                self.unit_price = self.variant.effective_price
            else:
                self.unit_price = self.product.effective_price
        super().save(*args, **kwargs)


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    class DeliveryMethod(models.TextChoices):
        STANDARD = "standard", "Standard Delivery (5–7 days)"
        EXPRESS = "express", "Express Delivery (2–3 days)"
        PICKUP = "pickup", "Store Pickup (Same day)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(
        max_length=20, unique=True, db_index=True, blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )

    # Pricing snapshot in KES integers
    subtotal = models.PositiveIntegerField()
    discount_amount = models.PositiveIntegerField(default=0)
    shipping_cost = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField()

    # Delivery
    delivery_method = models.CharField(
        max_length=20, choices=DeliveryMethod.choices
    )
    shipping_address = models.JSONField(
        help_text="Snapshot of delivery address at order time."
    )
    estimated_delivery = models.DateField(null=True, blank=True)
    tracking_number = models.CharField(max_length=200, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # Coupon
    coupon = models.ForeignKey(
        "coupons.Coupon",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    coupon_code = models.CharField(max_length=50, blank=True)

    # Customer snapshot
    customer_email = models.EmailField(db_index=True)
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20)

    # Notes
    customer_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["customer_email", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = generate_order_number()
        super().save(*args, **kwargs)

    def can_cancel(self):
        return self.status in [self.Status.PENDING, self.Status.CONFIRMED]

    def transition_to(self, new_status, note="", changed_by=None):
        """Transition order to a new status and log the change."""
        old_status = self.status
        self.status = new_status
        now = timezone.now()

        if new_status == self.Status.CONFIRMED:
            self.confirmed_at = now
        elif new_status == self.Status.SHIPPED:
            self.shipped_at = now
        elif new_status == self.Status.DELIVERED:
            self.delivered_at = now
        elif new_status == self.Status.CANCELLED:
            self.cancelled_at = now

        self.save()

        OrderStatusHistory.objects.create(
            order=self,
            status=new_status,
            note=note or f"Status changed from {old_status} to {new_status}.",
            changed_by=changed_by,
        )


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "products.Product",
        null=True,
        on_delete=models.SET_NULL,
        related_name="order_items",
    )
    variant = models.ForeignKey(
        "products.ProductVariant",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_items",
    )

    # Snapshots — survive product edits/deletions
    product_name = models.CharField(max_length=500)
    product_sku = models.CharField(max_length=100)
    variant_name = models.CharField(max_length=200, blank=True)
    product_image = models.URLField(blank=True)

    quantity = models.PositiveIntegerField()
    unit_price = models.PositiveIntegerField(help_text="Unit price in KES at order time.")
    total_price = models.PositiveIntegerField(help_text="unit_price × quantity in KES.")

    class Meta:
        db_table = "order_items"
        ordering = ["product_name"]
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.quantity}× {self.product_name} — {self.order.order_number}"


class OrderStatusHistory(models.Model):
    """Immutable audit trail for order status changes."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="status_history"
    )
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    note = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_status_changes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_status_history"
        ordering = ["-created_at"]
        verbose_name = "Status History"
        verbose_name_plural = "Status Histories"

    def __str__(self):
        return f"{self.order.order_number} → {self.status}"