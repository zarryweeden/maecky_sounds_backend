from django.urls import path
from .views import (
    InventoryListView,
    InventoryDetailView,
    AddStockView,
    AdjustStockView,
    InventoryLogListView,
    LowStockListView,
)

urlpatterns = [
    path("", InventoryListView.as_view(), name="inventory-list"),
    path("low-stock/", LowStockListView.as_view(), name="inventory-low-stock"),
    path("<slug:slug>/", InventoryDetailView.as_view(), name="inventory-detail"),
    path("<slug:slug>/add-stock/", AddStockView.as_view(), name="inventory-add-stock"),
    path("<slug:slug>/adjust/", AdjustStockView.as_view(), name="inventory-adjust"),
    path("<slug:slug>/logs/", InventoryLogListView.as_view(), name="inventory-logs"),
]