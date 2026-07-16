from django.urls import path
from .views import (
    ProductReviewListCreateView,
    ReviewDetailView,
    ReviewHelpfulView,
    ReviewSummaryView,
)

urlpatterns = [
    path("products/<slug:slug>/", ProductReviewListCreateView.as_view(), name="product-reviews"),
    path("products/<slug:slug>/summary/", ReviewSummaryView.as_view(), name="review-summary"),
    path("<uuid:pk>/", ReviewDetailView.as_view(), name="review-detail"),
    path("<uuid:pk>/helpful/", ReviewHelpfulView.as_view(), name="review-helpful"),
]