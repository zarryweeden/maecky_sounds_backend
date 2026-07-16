from django.urls import path
from .views import PlaceOrderView, OrderListView, OrderDetailView, CancelOrderView

urlpatterns = [
    path("", PlaceOrderView.as_view(), name="order-place"),
    path("history/", OrderListView.as_view(), name="order-list"),
    path("<str:order_number>/", OrderDetailView.as_view(), name="order-detail"),
    path("<str:order_number>/cancel/", CancelOrderView.as_view(), name="order-cancel"),
]