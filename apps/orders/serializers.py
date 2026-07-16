from rest_framework import serializers
from apps.products.serializers import ProductListSerializer
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory
from .utils import calculate_shipping, build_shipping_address_snapshot


class CartItemProductSerializer(serializers.Serializer):
    """Minimal product info embedded inside CartItem responses."""
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    sku = serializers.CharField()
    effective_price = serializers.IntegerField()
    in_stock = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    def get_in_stock(self, obj):
        try:
            return obj.inventory.is_in_stock
        except Exception:
            return False

    def get_primary_image(self, obj):
        request = self.context.get("request")
        images = obj.images.all()
        primary = next((img for img in images if img.is_primary), None)
        if not primary and images:
            primary = images[0]
        if primary:
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url
        return None


class CartItemSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()
    variant_info = serializers.SerializerMethodField()
    line_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "variant",
            "variant_info",
            "quantity",
            "unit_price",
            "line_total",
            "added_at",
        ]
        read_only_fields = ["id", "unit_price", "line_total", "added_at"]

    def get_product(self, obj):
        return CartItemProductSerializer(
            obj.product, context=self.context
        ).data

    def get_variant_info(self, obj):
        if obj.variant:
            return {
                "id": str(obj.variant.id),
                "name": obj.variant.name,
                "value": obj.variant.value,
            }
        return None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    coupon_info = serializers.SerializerMethodField()
    subtotal = serializers.IntegerField(read_only=True)
    discount_amount = serializers.IntegerField(read_only=True)
    shipping_cost = serializers.IntegerField(read_only=True)
    total = serializers.IntegerField(read_only=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "coupon_info",
            "subtotal",
            "discount_amount",
            "shipping_cost",
            "total",
            "total_items",
            "updated_at",
        ]
        read_only_fields = fields

    def get_coupon_info(self, obj):
        if not obj.coupon:
            return None
        return {
            "code": obj.coupon.code,
            "discount_type": obj.coupon.discount_type,
            "discount_value": obj.coupon.discount_value,
        }


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField(
        min_value=1,
        max_value=100,
        default=1,
        error_messages={"min_value": "Quantity must be at least 1."},
    )


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        min_value=1,
        max_value=100,
        error_messages={"min_value": "Quantity must be at least 1."},
    )


class ApplyCouponSerializer(serializers.Serializer):
    code = serializers.CharField(
        max_length=50,
        error_messages={"required": "Please enter a coupon code."},
    )

    def validate_code(self, value):
        return value.upper().strip()


class ShippingAddressSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=20)
    address_line1 = serializers.CharField(max_length=255)
    address_line2 = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100)
    county = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)


class PlaceOrderSerializer(serializers.Serializer):
    delivery_method = serializers.ChoiceField(choices=Order.DeliveryMethod.choices)
    shipping_address = ShippingAddressSerializer()
    payment_method = serializers.ChoiceField(
        choices=["mpesa", "card", "paypal", "bank"],
    )
    customer_notes = serializers.CharField(
        max_length=1000, required=False, allow_blank=True
    )
    use_saved_address_id = serializers.UUIDField(required=False, allow_null=True)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "variant_name",
            "product_image",
            "quantity",
            "unit_price",
            "total_price",
        ]
        read_only_fields = fields


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.CharField(
        source="changed_by.email", read_only=True, default=None
    )

    class Meta:
        model = OrderStatusHistory
        fields = ["id", "status", "note", "changed_by_email", "created_at"]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    delivery_method_display = serializers.CharField(
        source="get_delivery_method_display", read_only=True
    )
    can_cancel = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "status_display",
            "items",
            "subtotal",
            "discount_amount",
            "shipping_cost",
            "total",
            "delivery_method",
            "delivery_method_display",
            "shipping_address",
            "estimated_delivery",
            "tracking_number",
            "coupon_code",
            "customer_email",
            "customer_name",
            "customer_phone",
            "customer_notes",
            "can_cancel",
            "status_history",
            "created_at",
            "updated_at",
            "confirmed_at",
            "shipped_at",
            "delivered_at",
        ]
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for order list pages."""
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    item_count = serializers.SerializerMethodField()
    first_item_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "status_display",
            "total",
            "item_count",
            "first_item_name",
            "created_at",
            "estimated_delivery",
        ]
        read_only_fields = fields

    def get_item_count(self, obj):
        return obj.items.count()

    def get_first_item_name(self, obj):
        first = obj.items.first()
        return first.product_name if first else ""