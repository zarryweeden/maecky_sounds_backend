from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source="get_method_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "order_number",
            "method",
            "method_display",
            "status",
            "status_display",
            "amount",
            "currency",
            "transaction_id",
            "mpesa_receipt",
            "created_at",
            "updated_at",
            "completed_at",
        ]
        read_only_fields = fields


class MpesaInitiateSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    phone = serializers.CharField(max_length=20)

    def validate_phone(self, value):
        from .mpesa import format_phone
        try:
            return format_phone(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class StripeInitiateSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()


class StripeConfirmSerializer(serializers.Serializer):
    payment_intent_id = serializers.CharField()
    order_id = serializers.UUIDField()


class PaymentStatusSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField()