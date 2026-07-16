import logging
from datetime import timedelta

from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdminUser
from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from apps.inventory.models import Inventory

logger = logging.getLogger(__name__)


class DashboardView(APIView):
    """Admin dashboard — top-level KPIs."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        confirmed_statuses = [
            Order.Status.CONFIRMED,
            Order.Status.PROCESSING,
            Order.Status.SHIPPED,
            Order.Status.DELIVERED,
        ]

        # Revenue figures
        today_revenue = (
            Order.objects.filter(
                status__in=confirmed_statuses,
                created_at__gte=today_start,
            ).aggregate(total=Sum("total"))["total"] or 0
        )
        week_revenue = (
            Order.objects.filter(
                status__in=confirmed_statuses,
                created_at__gte=week_start,
            ).aggregate(total=Sum("total"))["total"] or 0
        )
        month_revenue = (
            Order.objects.filter(
                status__in=confirmed_statuses,
                created_at__gte=month_start,
            ).aggregate(total=Sum("total"))["total"] or 0
        )

        # Order counts
        pending_orders = Order.objects.filter(status=Order.Status.PENDING).count()
        total_orders = Order.objects.count()

        # Customer count
        from django.contrib.auth import get_user_model
        User = get_user_model()
        total_customers = User.objects.filter(is_staff=False, is_active=True).count()

        # Low stock count
        all_inv = Inventory.objects.filter(track_inventory=True)
        low_stock_count = sum(1 for inv in all_inv if inv.is_low_stock or not inv.is_in_stock)

        # Top products by revenue this month
        top_products = (
            OrderItem.objects.filter(
                order__status__in=confirmed_statuses,
                order__created_at__gte=month_start,
            )
            .values("product_name", "product_sku")
            .annotate(
                total_revenue=Sum("total_price"),
                units_sold=Sum("quantity"),
            )
            .order_by("-total_revenue")[:5]
        )

        # Recent orders
        recent_orders = (
            Order.objects.select_related("user")
            .order_by("-created_at")[:8]
        )

        from apps.orders.serializers import OrderListSerializer
        recent_orders_data = OrderListSerializer(
            recent_orders, many=True, context={"request": request}
        ).data

        return Response(
            {
                "today_revenue": today_revenue,
                "week_revenue": week_revenue,
                "month_revenue": month_revenue,
                "pending_orders": pending_orders,
                "total_orders": total_orders,
                "total_customers": total_customers,
                "low_stock_count": low_stock_count,
                "top_products": list(top_products),
                "recent_orders": recent_orders_data,
            }
        )


class SalesReportView(APIView):
    """Admin — sales by date range."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Parse date range from query params
        from datetime import date
        try:
            date_from_str = request.query_params.get("from")
            date_to_str = request.query_params.get("to")

            if date_from_str:
                from datetime import datetime
                date_from = datetime.strptime(date_from_str, "%Y-%m-%d").replace(
                    tzinfo=timezone.get_current_timezone()
                )
            else:
                date_from = timezone.now() - timedelta(days=30)

            if date_to_str:
                from datetime import datetime
                date_to = datetime.strptime(date_to_str, "%Y-%m-%d").replace(
                    tzinfo=timezone.get_current_timezone()
                )
            else:
                date_to = timezone.now()

        except ValueError:
            return Response(
                {"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."},
                status=400,
            )

        confirmed_statuses = [
            Order.Status.CONFIRMED,
            Order.Status.PROCESSING,
            Order.Status.SHIPPED,
            Order.Status.DELIVERED,
        ]

        orders = Order.objects.filter(
            status__in=confirmed_statuses,
            created_at__gte=date_from,
            created_at__lte=date_to,
        )

        # Daily breakdown
        from django.db.models.functions import TruncDate
        daily = (
            orders.annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(
                revenue=Sum("total"),
                order_count=Count("id"),
            )
            .order_by("date")
        )

        summary = orders.aggregate(
            total_revenue=Sum("total"),
            total_orders=Count("id"),
            avg_order_value=Avg("total"),
        )

        return Response(
            {
                "date_from": date_from.date().isoformat(),
                "date_to": date_to.date().isoformat(),
                "summary": {
                    "total_revenue": summary["total_revenue"] or 0,
                    "total_orders": summary["total_orders"] or 0,
                    "avg_order_value": round(summary["avg_order_value"] or 0),
                },
                "daily": list(daily),
            }
        )


class TopProductsView(APIView):
    """Admin — best-selling products."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        limit = int(request.query_params.get("limit", 10))
        period_days = int(request.query_params.get("days", 30))
        cutoff = timezone.now() - timedelta(days=period_days)

        confirmed_statuses = [
            Order.Status.CONFIRMED,
            Order.Status.PROCESSING,
            Order.Status.SHIPPED,
            Order.Status.DELIVERED,
        ]

        top = (
            OrderItem.objects.filter(
                order__status__in=confirmed_statuses,
                order__created_at__gte=cutoff,
            )
            .values(
                "product_name",
                "product_sku",
                "product_id",
            )
            .annotate(
                units_sold=Sum("quantity"),
                total_revenue=Sum("total_price"),
                order_count=Count("order", distinct=True),
            )
            .order_by("-units_sold")[:limit]
        )

        return Response(
            {
                "period_days": period_days,
                "results": list(top),
            }
        )


class LowStockReportView(APIView):
    """Admin — products at or below low-stock threshold."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        inventories = (
            Inventory.objects.filter(track_inventory=True)
            .select_related("product__brand", "product__category")
        )

        low_stock = []
        out_of_stock = []

        for inv in inventories:
            data = {
                "product_id": str(inv.product.id),
                "product_name": inv.product.name,
                "sku": inv.product.sku,
                "brand": inv.product.brand.name,
                "category": inv.product.category.name,
                "quantity": inv.quantity,
                "reserved": inv.reserved,
                "available": inv.available,
                "low_stock_threshold": inv.low_stock_threshold,
            }
            if not inv.is_in_stock:
                out_of_stock.append(data)
            elif inv.is_low_stock:
                low_stock.append(data)

        return Response(
            {
                "low_stock_count": len(low_stock),
                "out_of_stock_count": len(out_of_stock),
                "low_stock": sorted(low_stock, key=lambda x: x["available"]),
                "out_of_stock": out_of_stock,
            }
        )