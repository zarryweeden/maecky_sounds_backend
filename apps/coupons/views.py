from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.orders.views import get_or_create_cart
from .models import Coupon
from .serializers import CouponSerializer, ValidateCouponSerializer


class ValidateCouponView(APIView):
    """
    Validate a coupon code against the current cart.
    Works for both guests and authenticated users.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ValidateCouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        try:
            coupon = Coupon.objects.get(code=code, is_active=True)
        except Coupon.DoesNotExist:
            return Response(
                {
                    "valid": False,
                    "message": "This coupon code is invalid or has expired.",
                },
                status=status.HTTP_200_OK,
            )

        cart = get_or_create_cart(request)
        user = request.user if request.user.is_authenticated else None
        is_valid, error_msg = coupon.is_valid(user, cart)

        if not is_valid:
            return Response(
                {"valid": False, "message": error_msg},
                status=status.HTTP_200_OK,
            )

        discount = coupon.calculate_discount(cart)

        return Response(
            {
                "valid": True,
                "coupon": CouponSerializer(coupon).data,
                "discount_amount": discount,
                "message": (
                    f"{coupon.discount_value}% discount applied — you save KES {discount:,}"
                    if coupon.discount_type == "percentage"
                    else f"KES {discount:,} discount applied"
                ),
            }
        )