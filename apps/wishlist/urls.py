from django.urls import path
from .views import (
    WishlistListView,
    WishlistAddView,
    WishlistRemoveView,
    WishlistToggleView,
    WishlistMoveToCartView,
)

urlpatterns = [
    path("", WishlistListView.as_view(), name="wishlist-list"),
    path("add/", WishlistAddView.as_view(), name="wishlist-add"),
    path("toggle/", WishlistToggleView.as_view(), name="wishlist-toggle"),
    path("move-to-cart/", WishlistMoveToCartView.as_view(), name="wishlist-move-to-cart"),
    path("<uuid:product_id>/", WishlistRemoveView.as_view(), name="wishlist-remove"),
]