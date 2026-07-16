from rest_framework import serializers
from .models import Inventory, InventoryLog


class InventorySerializer(serializers.ModelSerializer):
    available = serializers.IntegerField(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)

    class Meta:
        model = Inventory
        fields = [
            "id",
            "product_name",
            "product_sku",
            "quantity",
            "reserved",
            "available",
            "low_stock_threshold",
            "track_inventory",
            "allow_backorder",
            "is_in_stock",
            "is_low_stock",
            "updated_at",
        ]
        read_only_fields = ["id", "reserved", "available", "updated_at"]


class InventoryLogSerializer(serializers.ModelSerializer):
    created_by_email = serializers.CharField(
        source="created_by.email", read_only=True, default=None
    )

    class Meta:
        model = InventoryLog
        fields = [
            "id",
            "reason",
            "delta",
            "quantity_after",
            "reference",
            "note",
            "created_by_email",
            "created_at",
        ]
        read_only_fields = fields


class StockAdjustmentSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
    reference = serializers.CharField(max_length=200, required=False, allow_blank=True)


class AddStockSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        min_value=1,
        error_messages={"min_value": "Quantity to add must be at least 1."},
    )
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
    reference = serializers.CharField(max_length=200, required=False, allow_blank=True)