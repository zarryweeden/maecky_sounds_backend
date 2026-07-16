from django.urls import path
from .views import (
    ProductListView,
    ProductDetailView,
    ProductIncrementViewView,
    ProductRelatedView,
    FeaturedProductsView,
    NewArrivalsView,
    OnSaleView,
    BestsellersView,
)

urlpatterns = [
    path("", ProductListView.as_view(), name="product-list"),
    path("featured/", FeaturedProductsView.as_view(), name="product-featured"),
    path("new-arrivals/", NewArrivalsView.as_view(), name="product-new-arrivals"),
    path("on-sale/", OnSaleView.as_view(), name="product-on-sale"),
    path("bestsellers/", BestsellersView.as_view(), name="product-bestsellers"),
    path("<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    path("<slug:slug>/view/", ProductIncrementViewView.as_view(), name="product-view"),
    path("<slug:slug>/related/", ProductRelatedView.as_view(), name="product-related"),
]