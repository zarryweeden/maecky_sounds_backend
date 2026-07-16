import uuid
from django.db import models
from django.conf import settings


class Inventory(models.Model):
    """One-to-one with Product. Tracks stock levels."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.OneToOneField(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(
        default=0,
        help_text="Units held by pending/confirmed orders.",
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=5,
        help_text="Alert when available stock drops to or below this number.",
    )
    track_inventory = models.BooleanField(
        default=True,
        help_text="If False, product is treated as always in stock.",
    )
    allow_backorder = models.BooleanField(
        default=False,
        help_text="Allow orders even when out of stock.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory"
        verbose_name = "Inventory"
        verbose_name_plural = "Inventory"

    def __str__(self):
        return f"{self.product.name} — {self.available} available"

    @property
    def available(self):
        """Units available for purchase."""
        return max(0, self.quantity - self.reserved)

    @property
    def is_in_stock(self):
        if not self.track_inventory:
            return True
        return self.available > 0 or self.allow_backorder

    @property
    def is_low_stock(self):
        if not self.track_inventory:
            return False
        return 0 < self.available <= self.low_stock_threshold

    def reserve(self, quantity, reference="", note=""):
        """Reserve units for a pending order. Raises ValueError if not enough stock."""
        if self.track_inventory and not self.allow_backorder:
            if self.available < quantity:
                raise ValueError(
                    f"Cannot reserve {quantity} units of '{self.product.name}'. "
                    f"Only {self.available} available."
                )
        self.reserved = models.F("reserved") + quantity
        self.save(update_fields=["reserved"])
        self.refresh_from_db()
        self._log(
            reason=InventoryLog.Reason.RESERVED,
            delta=quantity,
            reference=reference,
            note=note,
        )

    def release(self, quantity, reference="", note=""):
        """Release reserved units (e.g. order cancelled)."""
        release_qty = min(quantity, self.reserved)
        self.reserved = max(0, self.reserved - release_qty)
        self.save(update_fields=["reserved"])
        self._log(
            reason=InventoryLog.Reason.RELEASED,
            delta=-release_qty,
            reference=reference,
            note=note,
        )

    def confirm_sale(self, quantity, reference="", note=""):
        """Confirm a sale: decrement both quantity and reserved."""
        self.quantity = max(0, self.quantity - quantity)
        self.reserved = max(0, self.reserved - quantity)
        self.save(update_fields=["quantity", "reserved"])
        self._log(
            reason=InventoryLog.Reason.SALE,
            delta=-quantity,
            reference=reference,
            note=note,
        )

    def add_stock(self, quantity, reference="", note="", user=None):
        """Add incoming stock."""
        self.quantity = models.F("quantity") + quantity
        self.save(update_fields=["quantity"])
        self.refresh_from_db()
        self._log(
            reason=InventoryLog.Reason.PURCHASE,
            delta=quantity,
            reference=reference,
            note=note,
            user=user,
        )

    def adjust(self, new_quantity, reference="", note="", user=None):
        """Manual adjustment to set quantity to a specific value."""
        delta = new_quantity - self.quantity
        self.quantity = new_quantity
        self.save(update_fields=["quantity"])
        self._log(
            reason=InventoryLog.Reason.ADJUSTMENT,
            delta=delta,
            reference=reference,
            note=note,
            user=user,
        )

    def _log(self, reason, delta, reference="", note="", user=None):
        InventoryLog.objects.create(
            inventory=self,
            reason=reason,
            delta=delta,
            quantity_after=self.quantity,
            reference=reference,
            note=note,
            created_by=user,
        )


class InventoryLog(models.Model):
    """Immutable audit trail of every stock change."""

    class Reason(models.TextChoices):
        PURCHASE = "purchase", "Purchase Order"
        SALE = "sale", "Sale"
        RETURN = "return", "Customer Return"
        ADJUSTMENT = "adjustment", "Manual Adjustment"
        RESERVED = "reserved", "Order Reserved"
        RELEASED = "released", "Reservation Released"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    reason = models.CharField(max_length=20, choices=Reason.choices, db_index=True)
    delta = models.IntegerField(help_text="+N = stock added, -N = stock removed")
    quantity_after = models.IntegerField()
    reference = models.CharField(
        max_length=200, blank=True, db_index=True,
        help_text="Order number, purchase order ref, etc.",
    )
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "inventory_logs"
        ordering = ["-created_at"]
        verbose_name = "Inventory Log"
        verbose_name_plural = "Inventory Logs"

    def __str__(self):
        sign = "+" if self.delta >= 0 else ""
        return f"{self.inventory.product.name} | {self.reason} | {sign}{self.delta}"