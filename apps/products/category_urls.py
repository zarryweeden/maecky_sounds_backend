from django.urls import path
from .views import CategoryListView, CategoryDetailView, CategoryProductsView

urlpatterns = [
    path("", CategoryListView.as_view(), name="category-list"),
    path("<slug:slug>/", CategoryDetailView.as_view(), name="category-detail"),
    path("<slug:slug>/products/", CategoryProductsView.as_view(), name="category-products"),
]