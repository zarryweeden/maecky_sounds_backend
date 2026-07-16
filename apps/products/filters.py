from django.db.models import F
import django_filters
from django_filters import rest_framework as filters
from .models import Product, Category, Brand


class ProductFilter(filters.FilterSet):
    # Price range
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    # Category filtering — by slug or by slug of parent
    category = django_filters.CharFilter(field_name="category__slug", lookup_expr="exact")
    category_id = django_filters.UUIDFilter(field_name="category__id")

    # Brand filtering — comma-separated slugs
    brand = django_filters.CharFilter(method="filter_brand")

    # Condition
    condition = django_filters.MultipleChoiceFilter(choices=Product.Condition.choices)

    # Boolean flags
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")
    is_new = django_filters.BooleanFilter(field_name="is_new")
    is_hot = django_filters.BooleanFilter(field_name="is_hot")
    is_featured = django_filters.BooleanFilter(field_name="is_featured")
    is_sale = django_filters.BooleanFilter(method="filter_is_sale")

    # Rating minimum
    rating = django_filters.NumberFilter(field_name="average_rating", lookup_expr="gte")

    # Tag filtering
    tags = django_filters.CharFilter(method="filter_tags")

    def filter_brand(self, queryset, name, value):
        """Support comma-separated brand slugs: ?brand=fender,gibson"""
        slugs = [s.strip() for s in value.split(",") if s.strip()]
        if slugs:
            return queryset.filter(brand__slug__in=slugs)
        return queryset

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(
                inventory__quantity__gt=F("inventory__reserved")
            )
        return queryset

    def filter_is_sale(self, queryset, name, value):
        if value:
            return queryset.filter(
                sale_price__isnull=False,
                sale_price__lt=F("price"),
            )
        return queryset

    def filter_tags(self, queryset, name, value):
        """Support comma-separated tags: ?tags=jazz,acoustic"""
        tag_list = [t.strip() for t in value.split(",") if t.strip()]
        if tag_list:
            return queryset.filter(tags__slug__in=tag_list).distinct()
        return queryset

    class Meta:
        model = Product
        fields = ["is_active", "is_featured", "is_new", "is_hot", "condition"]