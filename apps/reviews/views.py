import logging
from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Product
from apps.products.pagination import StandardResultsPagination
from apps.orders.models import Order
from .models import Review, ReviewHelpful
from .serializers import (
    ReviewSerializer,
    CreateReviewSerializer,
    ReviewSummarySerializer,
)

logger = logging.getLogger(__name__)


def _check_verified_purchase(user, product):
    """Return True if the user has a delivered order containing this product."""
    return Order.objects.filter(
        user=user,
        status=Order.Status.DELIVERED,
        items__product=product,
    ).exists()


class ProductReviewListCreateView(generics.ListCreateAPIView):
    pagination_class = StandardResultsPagination

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateReviewSerializer
        return ReviewSerializer

    def get_queryset(self):
        slug = self.kwargs["slug"]
        return (
            Review.objects.filter(
                product__slug=slug,
                is_approved=True,
            )
            .select_related("user")
            .order_by("-helpful_count", "-created_at")
        )

    def create(self, request, *args, **kwargs):
        slug = self.kwargs["slug"]
        try:
            product = Product.objects.get(slug=slug, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {"status": "error", "message": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # One review per user per product
        if Review.objects.filter(product=product, user=request.user).exists():
            return Response(
                {
                    "status": "error",
                    "message": "You have already reviewed this product.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CreateReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_verified = _check_verified_purchase(request.user, product)

        review = Review.objects.create(
            product=product,
            user=request.user,
            is_verified=is_verified,
            **serializer.validated_data,
        )

        return Response(
            ReviewSerializer(review, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        instance = self.get_object()
        serializer = CreateReviewSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            ReviewSerializer(instance, context={"request": request}).data
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"status": "success", "message": "Review deleted."},
            status=status.HTTP_200_OK,
        )


class ReviewHelpfulView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            review = Review.objects.get(pk=pk, is_approved=True)
        except Review.DoesNotExist:
            return Response(
                {"status": "error", "message": "Review not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if review.user == request.user:
            return Response(
                {"status": "error", "message": "You cannot vote on your own review."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_helpful = request.data.get("helpful", True)

        vote, created = ReviewHelpful.objects.get_or_create(
            review=review,
            user=request.user,
            defaults={"is_helpful": is_helpful},
        )

        if not created:
            vote.is_helpful = is_helpful
            vote.save(update_fields=["is_helpful"])

        # Recalculate helpful counts
        review.helpful_count = ReviewHelpful.objects.filter(
            review=review, is_helpful=True
        ).count()
        review.unhelpful_count = ReviewHelpful.objects.filter(
            review=review, is_helpful=False
        ).count()
        review.save(update_fields=["helpful_count", "unhelpful_count"])

        return Response(
            {
                "status": "success",
                "helpful_count": review.helpful_count,
                "unhelpful_count": review.unhelpful_count,
            }
        )


class ReviewSummaryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            product = Product.objects.get(slug=slug, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {"status": "error", "message": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        reviews = Review.objects.filter(product=product, is_approved=True)

        dist = {str(i): 0 for i in range(1, 6)}
        for r in reviews.values("rating").annotate(count=Count("id")):
            dist[str(r["rating"])] = r["count"]

        verified_count = reviews.filter(is_verified=True).count()

        return Response(
            {
                "average_rating": float(product.average_rating),
                "review_count": product.review_count,
                "rating_distribution": dist,
                "verified_count": verified_count,
            }
        )