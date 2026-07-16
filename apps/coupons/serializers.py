from rest_framework import serializers
from .models import Coupon


class CouponSerializer(serializers.ModelSerializer):
    discount_type_display = serializers.CharField(
        source="get_discount_type_display", read_only=True
    )

    class Meta:
        model = Coupon
        fields = [
            "code",
            "description",
            "discount_type",
            "discount_type_display",
            "discount_value",
            "minimum_order",
            "maximum_discount",
            "valid_from",
            "valid_until",
        ]
        read_only_fields = fields


class ValidateCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)

    def validate_code(self, value):
        return value.upper().strip()