from django.urls import path
from .views import BrandListView, BrandProductsView

urlpatterns = [
    path("", BrandListView.as_view(), name="brand-list"),
    path("<slug:slug>/products/", BrandProductsView.as_view(), name="brand-products"),
]