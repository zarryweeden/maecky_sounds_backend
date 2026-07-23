from django.db.models import Avg
from rest_framework import serializers
from .models import (
    Category,
    Brand,
    Product,
    ProductImage,
    ProductSpecification,
    ProductVariant,
    Tag,
)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]
        read_only_fields = fields


class CategoryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon"]
        read_only_fields = fields


class CategoryChildSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id", "name", "slug", "description",
            "image", "icon", "product_count", "children",
        ]
        read_only_fields = fields

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategoryChildSerializer(children, many=True, context=self.context).data


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)
    children = CategoryChildSerializer(many=True, read_only=True)
    parent = CategoryMiniSerializer(read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "featured",
            "sort_order",
        ]
        read_only_fields = fields


class BrandMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "logo"]
        read_only_fields = fields


class BrandSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Brand
        fields = [
            "id", "name", "slug", "logo",
            "description", "website", "product_count",
        ]
        read_only_fields = fields


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary", "sort_order"]
        read_only_fields = fields


class ProductSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpecification
        fields = ["id", "key", "value", "sort_order"]
        read_only_fields = fields


class ProductVariantSerializer(serializers.ModelSerializer):
    effective_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            "id", "name", "value", "sku_suffix",
            "price_delta", "image", "is_active", "effective_price",
        ]
        read_only_fields = fields


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for product list pages."""
    brand = BrandMiniSerializer(read_only=True)
    category = CategoryMiniSerializer(read_only=True)
    primary_image = serializers.SerializerMethodField()
    effective_price = serializers.IntegerField(read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    in_stock = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "sku", "name", "slug",
            "brand", "category",
            "price", "sale_price", "effective_price",
            "is_on_sale", "discount_percent",
            "primary_image",
            "average_rating", "review_count",
            "is_featured", "is_new", "is_hot",
            "condition", "in_stock", "tags",
            "created_at",
        ]
        read_only_fields = fields

    def get_primary_image(self, obj):
        # Images are prefetched — avoid extra query
        images = obj.images.all()
        primary = next((img for img in images if img.is_primary), None)
        if not primary and images:
            primary = images[0]
        if primary:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url
        return None

    def get_in_stock(self, obj):
        try:
            inv = obj.inventory
            return inv.is_in_stock
        except Exception:
            return False

    def get_tags(self, obj):
        return [tag.slug for tag in obj.tags.all()]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full serializer for product detail page."""
    brand = BrandMiniSerializer(read_only=True)
    category = CategoryMiniSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    effective_price = serializers.IntegerField(read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    inventory = serializers.SerializerMethodField()
    is_in_wishlist = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "sku", "name", "slug",
            "brand", "category",
            "price", "sale_price", "effective_price",
            "is_on_sale", "discount_percent",
            "short_description", "description",
            "images", "primary_image",
            "specifications", "variants", "tags",
            "average_rating", "review_count",
            "is_featured", "is_new", "is_hot",
            "condition", "weight",
            "inventory", "is_in_wishlist",
            "total_sold", "view_count",
            "meta_title", "meta_description",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_inventory(self, obj):
        try:
            inv = obj.inventory
            return {
                "in_stock": inv.is_in_stock,
                "quantity": inv.available,
                "is_low_stock": inv.is_low_stock,
                "allow_backorder": inv.allow_backorder,
            }
        except Exception:
            return {"in_stock": False, "quantity": 0, "is_low_stock": False, "allow_backorder": False}

    def get_is_in_wishlist(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.wishlist_items.filter(user=request.user).exists()
        return False

    def get_primary_image(self, obj):
        images = obj.images.all()
        primary = next((img for img in images if img.is_primary), None)
        if not primary and images:
            primary = images[0]
        if primary:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url
        return None