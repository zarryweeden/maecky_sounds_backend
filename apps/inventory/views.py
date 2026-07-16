import logging
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminUser
from .models import Inventory, InventoryLog
from .serializers import (
    InventorySerializer,
    InventoryLogSerializer,
    StockAdjustmentSerializer,
    AddStockSerializer,
)

logger = logging.getLogger(__name__)


class InventoryListView(generics.ListAPIView):
    """Admin: list all inventory records with filtering."""
    permission_classes = [IsAdminUser]
    serializer_class = InventorySerializer

    def get_queryset(self):
        qs = Inventory.objects.select_related("product").order_by("product__name")
        # Filter by low stock
        if self.request.query_params.get("low_stock"):
            return [inv for inv in qs if inv.is_low_stock]
        # Filter by out of stock
        if self.request.query_params.get("out_of_stock"):
            return [inv for inv in qs if not inv.is_in_stock]
        return qs


class InventoryDetailView(generics.RetrieveUpdateAPIView):
    """Admin: view and update an inventory record."""
    permission_classes = [IsAdminUser]
    serializer_class = InventorySerializer
    queryset = Inventory.objects.select_related("product")
    lookup_field = "product__slug"
    lookup_url_kwarg = "slug"


class AddStockView(APIView):
    """Admin: add incoming stock to a product."""
    permission_classes = [IsAdminUser]

    def post(self, request, slug):
        try:
            inventory = Inventory.objects.select_related("product").get(
                product__slug=slug
            )
        except Inventory.DoesNotExist:
            return Response(
                {"status": "error", "message": "Inventory record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AddStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inventory.add_stock(
            quantity=serializer.validated_data["quantity"],
            reference=serializer.validated_data.get("reference", ""),
            note=serializer.validated_data.get("note", ""),
            user=request.user,
        )

        return Response(
            {
                "status": "success",
                "message": f"Added {serializer.validated_data['quantity']} units.",
                "inventory": InventorySerializer(inventory).data,
            }
        )


class AdjustStockView(APIView):
    """Admin: set stock to a specific quantity."""
    permission_classes = [IsAdminUser]

    def post(self, request, slug):
        try:
            inventory = Inventory.objects.select_related("product").get(
                product__slug=slug
            )
        except Inventory.DoesNotExist:
            return Response(
                {"status": "error", "message": "Inventory record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inventory.adjust(
            new_quantity=serializer.validated_data["quantity"],
            reference=serializer.validated_data.get("reference", ""),
            note=serializer.validated_data.get("note", ""),
            user=request.user,
        )

        return Response(
            {
                "status": "success",
                "message": f"Stock adjusted to {serializer.validated_data['quantity']} units.",
                "inventory": InventorySerializer(inventory).data,
            }
        )


class InventoryLogListView(generics.ListAPIView):
    """Admin: view stock movement history for a product."""
    permission_classes = [IsAdminUser]
    serializer_class = InventoryLogSerializer

    def get_queryset(self):
        slug = self.kwargs["slug"]
        return InventoryLog.objects.filter(
            inventory__product__slug=slug
        ).select_related("created_by").order_by("-created_at")


class LowStockListView(generics.ListAPIView):
    """Admin: get all products with low or zero stock."""
    permission_classes = [IsAdminUser]
    serializer_class = InventorySerializer

    def get_queryset(self):
        all_inv = Inventory.objects.select_related("product").filter(track_inventory=True)
        return [inv for inv in all_inv if inv.is_low_stock or not inv.is_in_stock]