from rest_framework import serializers
from apps.products.serializers import ProductListSerializer
from .models import WishlistItem


class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ["id", "product", "added_at"]
        read_only_fields = fields


class AddToWishlistSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()


class ToggleWishlistSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()