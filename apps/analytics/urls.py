from django.urls import path
from .views import (
    DashboardView,
    SalesReportView,
    TopProductsView,
    LowStockReportView,
)

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="analytics-dashboard"),
    path("sales/", SalesReportView.as_view(), name="analytics-sales"),
    path("products/top/", TopProductsView.as_view(), name="analytics-top-products"),
    path("inventory/low-stock/", LowStockReportView.as_view(), name="analytics-low-stock"),
]