from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Product
from apps.orders.views import get_or_create_cart
from apps.orders.models import CartItem
from .models import WishlistItem
from .serializers import (
    WishlistItemSerializer,
    AddToWishlistSerializer,
    ToggleWishlistSerializer,
)


class WishlistListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WishlistItemSerializer

    def get_queryset(self):
        return (
            WishlistItem.objects.filter(user=self.request.user)
            .select_related("product__brand", "product__category", "product__inventory")
            .prefetch_related("product__images", "product__tags")
            .order_by("-added_at")
        )


class WishlistAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AddToWishlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            product = Product.objects.get(
                id=serializer.validated_data["product_id"],
                is_active=True,
            )
        except Product.DoesNotExist:
            return Response(
                {"status": "error", "message": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        item, created = WishlistItem.objects.get_or_create(
            user=request.user,
            product=product,
        )

        if not created:
            return Response(
                {"status": "info", "message": "Product is already in your wishlist."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "status": "success",
                "message": f"'{product.name}' added to your wishlist.",
                "item": WishlistItemSerializer(item, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class WishlistRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, product_id):
        deleted, _ = WishlistItem.objects.filter(
            user=request.user,
            product_id=product_id,
        ).delete()

        if not deleted:
            return Response(
                {"status": "error", "message": "Product not found in your wishlist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"status": "success", "message": "Removed from wishlist."}
        )


class WishlistToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ToggleWishlistSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            product = Product.objects.get(
                id=serializer.validated_data["product_id"],
                is_active=True,
            )
        except Product.DoesNotExist:
            return Response(
                {"status": "error", "message": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        item = WishlistItem.objects.filter(user=request.user, product=product).first()

        if item:
            item.delete()
            return Response(
                {
                    "status": "success",
                    "action": "removed",
                    "message": f"'{product.name}' removed from your wishlist.",
                    "in_wishlist": False,
                }
            )

        WishlistItem.objects.create(user=request.user, product=product)
        return Response(
            {
                "status": "success",
                "action": "added",
                "message": f"'{product.name}' added to your wishlist.",
                "in_wishlist": True,
            },
            status=status.HTTP_201_CREATED,
        )


class WishlistMoveToCartView(APIView):
    """Move all wishlist items to the active cart."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        wishlist_items = WishlistItem.objects.filter(
            user=request.user
        ).select_related("product__inventory")

        if not wishlist_items.exists():
            return Response(
                {"status": "info", "message": "Your wishlist is empty."}
            )

        cart = get_or_create_cart(request)
        moved = 0
        skipped = []

        for item in wishlist_items:
            product = item.product
            if not product.in_stock:
                skipped.append(product.name)
                continue

            existing = cart.items.filter(product=product).first()
            if existing:
                existing.quantity = min(
                    existing.quantity + 1,
                    product.inventory.available if hasattr(product, "inventory") else 999,
                )
                existing.save(update_fields=["quantity"])
            else:
                CartItem.objects.create(
                    cart=cart,
                    product=product,
                    quantity=1,
                    unit_price=product.effective_price,
                )
            moved += 1

        return Response(
            {
                "status": "success",
                "message": f"Moved {moved} item(s) to your cart.",
                "moved": moved,
                "skipped": skipped,
            }
        )