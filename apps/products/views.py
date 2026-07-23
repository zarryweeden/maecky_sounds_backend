import logging
from django.db.models import Count, Q, F
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ProductFilter
from .models import Category, Brand, Product
from .pagination import StandardResultsPagination
from .serializers import (
    CategorySerializer,
    BrandSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
)

logger = logging.getLogger(__name__)

PRODUCT_QUERYSET_BASE = (
    Product.objects.select_related("brand", "category", "inventory")
    .prefetch_related("images", "tags", "specifications", "variants")
    .filter(is_active=True)
)


def get_ordering(sort_param):
    ORDERING_MAP = {
        "price":    "price",
        "-price":   "-price",
        "newest":   "-created_at",
        "-newest":  "created_at",
        "rating":   "-average_rating",
        "popular":  "-total_sold",
        "name":     "name",
        "-name":    "-name",
    }
    return ORDERING_MAP.get(sort_param, "-total_sold")


# ── Product Views ─────────────────────────────────────────────────────────────

class ProductListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = StandardResultsPagination
    filterset_class = ProductFilter
    search_fields = ["name", "brand__name", "description", "sku", "tags__name"]

    def get_queryset(self):
        qs = PRODUCT_QUERYSET_BASE
        ordering = get_ordering(self.request.query_params.get("ordering", "popular"))
        return qs.order_by(ordering)


class ProductDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return PRODUCT_QUERYSET_BASE.prefetch_related(
            "wishlist_items",
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count atomically
        Product.objects.filter(pk=instance.pk).update(view_count=F("view_count") + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ProductIncrementViewView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, slug):
        updated = Product.objects.filter(slug=slug, is_active=True).update(
            view_count=F("view_count") + 1
        )
        if not updated:
            return Response(
                {"status": "error", "message": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"status": "success"})


class ProductRelatedView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = None

    def get_queryset(self):
        slug = self.kwargs["slug"]
        try:
            product = Product.objects.get(slug=slug, is_active=True)
        except Product.DoesNotExist:
            return Product.objects.none()

        return (
            PRODUCT_QUERYSET_BASE.filter(
                Q(category=product.category) | Q(brand=product.brand)
            )
            .exclude(pk=product.pk)
            .order_by("-total_sold")[:8]
        )


class FeaturedProductsView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = None

    def get_queryset(self):
        return PRODUCT_QUERYSET_BASE.filter(is_featured=True).order_by("-total_sold")[:8]

    @method_decorator(cache_page(60 * 15))
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class NewArrivalsView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = None

    def get_queryset(self):
        return PRODUCT_QUERYSET_BASE.filter(is_new=True).order_by("-created_at")[:8]

    @method_decorator(cache_page(60 * 15))
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class OnSaleView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        return PRODUCT_QUERYSET_BASE.filter(
            sale_price__isnull=False,
            sale_price__lt=F("price"),
        ).order_by("-total_sold")


class BestsellersView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = None

    def get_queryset(self):
        return PRODUCT_QUERYSET_BASE.order_by("-total_sold")[:8]

    @method_decorator(cache_page(60 * 30))
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


# ── Category Views ────────────────────────────────────────────────────────────

class CategoryListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    pagination_class = None

    def get_queryset(self):

        featured = self.request.query_params.get("featured")
        cache_key = f"categories:{featured}"

        queryset = (
            Category.objects.filter(
                is_active=True,
                parent__isnull=True
            )
            .annotate(
                product_count=Count(
                    "products",
                    filter=Q(products__is_active=True)
                )
            )
            .prefetch_related("children")
            .order_by("display_order", "name")
        )

        if featured == "true":
            queryset = queryset.filter(featured=True)

        return queryset

    def list(self, request, *args, **kwargs):
        # Cache the category tree for 1 hour
        cache_key = "categories:tree"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, 60 * 60)
        return response


class CategoryDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Category.objects.filter(is_active=True)
            .annotate(product_count=Count("products", filter=Q(products__is_active=True)))
            .prefetch_related("children")
        )


class CategoryProductsView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = StandardResultsPagination
    filterset_class = ProductFilter
    search_fields = ["name", "brand__name", "description"]

    def get_queryset(self):
        slug = self.kwargs["slug"]

        # Get the category and all its descendants
        try:
            category = Category.objects.get(slug=slug, is_active=True)
        except Category.DoesNotExist:
            return Product.objects.none()

        # Include products from child categories too
        category_ids = [category.id] + list(
            Category.objects.filter(parent=category, is_active=True).values_list("id", flat=True)
        )

        ordering = get_ordering(self.request.query_params.get("ordering", "popular"))
        return PRODUCT_QUERYSET_BASE.filter(
            category__id__in=category_ids
        ).order_by(ordering)


# ── Brand Views ───────────────────────────────────────────────────────────────

class BrandListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = BrandSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Brand.objects.filter(is_active=True)
            .annotate(product_count=Count("products", filter=Q(products__is_active=True)))
            .order_by("sort_order", "name")
        )

    @method_decorator(cache_page(60 * 60))
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class BrandProductsView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = StandardResultsPagination
    filterset_class = ProductFilter

    def get_queryset(self):
        slug = self.kwargs["slug"]
        ordering = get_ordering(self.request.query_params.get("ordering", "popular"))
        return PRODUCT_QUERYSET_BASE.filter(brand__slug=slug).order_by(ordering)


# ── Search Views ──────────────────────────────────────────────────────────────

class SearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

        query = request.query_params.get("q", "").strip()
        if not query or len(query) < 2:
            return Response(
                {
                    "products": {"results": [], "total": 0},
                    "categories": {"results": [], "total": 0},
                    "brands": {"results": [], "total": 0},
                    "query": query,
                    "total": 0,
                }
            )

        # Full-text product search
        search_vector = SearchVector("name", weight="A") + SearchVector("description", weight="B")
        search_query = SearchQuery(query)

        products = (
            PRODUCT_QUERYSET_BASE.annotate(
                rank=SearchRank(search_vector, search_query)
            )
            .filter(
                Q(rank__gte=0.01)
                | Q(name__icontains=query)
                | Q(brand__name__icontains=query)
                | Q(tags__name__icontains=query)
            )
            .distinct()
            .order_by("-rank", "-total_sold")[:12]
        )

        categories = (
            Category.objects.filter(is_active=True, name__icontains=query)
            .annotate(product_count=Count("products", filter=Q(products__is_active=True)))
            [:5]
        )

        brands = Brand.objects.filter(is_active=True, name__icontains=query)[:5]

        product_data = ProductListSerializer(products, many=True, context={"request": request}).data
        category_data = CategorySerializer(categories, many=True).data
        brand_data = BrandSerializer(brands, many=True).data

        total = len(product_data) + len(category_data) + len(brand_data)

        return Response(
            {
                "products": {"results": product_data, "total": len(product_data)},
                "categories": {"results": category_data, "total": len(category_data)},
                "brands": {"results": brand_data, "total": len(brand_data)},
                "query": query,
                "total": total,
            }
        )


class SearchSuggestionsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query or len(query) < 2:
            return Response({"products": [], "categories": [], "brands": []})

        products = (
            PRODUCT_QUERYSET_BASE.filter(name__icontains=query)
            .values("name", "slug")[:5]
        )
        categories = (
            Category.objects.filter(is_active=True, name__icontains=query)
            .values("name", "slug")[:3]
        )
        brands = (
            Brand.objects.filter(is_active=True, name__icontains=query)
            .values("name", "slug")[:3]
        )

        return Response(
            {
                "products": list(products),
                "categories": list(categories),
                "brands": list(brands),
            }
        )