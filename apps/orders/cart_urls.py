from django.urls import path
from .views import (
    CartDetailView,
    CartAddItemView,
    CartItemUpdateView,
    CartClearView,
    CartApplyCouponView,
    CartRemoveCouponView,
    CartSummaryView,
    CartMergeView,
)

urlpatterns = [
    path("", CartDetailView.as_view(), name="cart-detail"),
    path("items/", CartAddItemView.as_view(), name="cart-add-item"),
    path("items/<uuid:item_id>/", CartItemUpdateView.as_view(), name="cart-item-update"),
    path("clear/", CartClearView.as_view(), name="cart-clear"),
    path("coupon/apply/", CartApplyCouponView.as_view(), name="cart-apply-coupon"),
    path("coupon/remove/", CartRemoveCouponView.as_view(), name="cart-remove-coupon"),
    path("summary/", CartSummaryView.as_view(), name="cart-summary"),
    path("merge/", CartMergeView.as_view(), name="cart-merge"),
]