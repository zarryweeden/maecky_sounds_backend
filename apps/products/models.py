import uuid
from django.db import models
from django.utils.text import slugify


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tags"
        ordering = ["name"]
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(unique=True, db_index=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", null=True, blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    featured = models.BooleanField(
        default=False,
        help_text="Display this category on the homepage."
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first."
    )

    class Meta:
        db_table = "categories"
        ordering = ["sort_order", "name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=["is_active", "sort_order"]),
            models.Index(fields=["parent", "is_active"]),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def full_path(self):
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name


class Brand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True, db_index=True)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to="brands/", null=True, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "brands"
        ordering = ["sort_order", "name"]
        verbose_name = "Brand"
        verbose_name_plural = "Brands"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    class Condition(models.TextChoices):
        NEW = "new", "New"
        USED = "used", "Used"
        REFURBISHED = "refurbished", "Refurbished"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=500, db_index=True)
    slug = models.SlugField(unique=True, max_length=600, db_index=True)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")

    # Pricing in KES (integers — no floating point money)
    price = models.PositiveIntegerField(help_text="Regular price in KES")
    sale_price = models.PositiveIntegerField(
        null=True, blank=True, help_text="Sale price in KES. Leave blank if not on sale."
    )
    cost_price = models.PositiveIntegerField(
        null=True, blank=True, help_text="Internal cost price. Never exposed in API."
    )

    # Content
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)

    # Flags
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_new = models.BooleanField(default=False, db_index=True)
    is_hot = models.BooleanField(default=False, db_index=True)

    # Meta
    condition = models.CharField(
        max_length=20, choices=Condition.choices, default=Condition.NEW
    )
    weight = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Weight in kg"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")

    # Computed / cached fields — updated by signals
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)
    total_sold = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)

    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]
        verbose_name = "Product"
        verbose_name_plural = "Products"
        indexes = [
            models.Index(fields=["is_active", "is_featured"]),
            models.Index(fields=["is_active", "category"]),
            models.Index(fields=["is_active", "brand"]),
            models.Index(fields=["is_active", "-created_at"]),
            models.Index(fields=["is_active", "-total_sold"]),
            models.Index(fields=["is_active", "price"]),
            models.Index(fields=["is_active", "-average_rating"]),
            models.Index(fields=["is_active", "is_new"]),
            models.Index(fields=["is_active", "is_hot"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def effective_price(self):
        """Return sale price if valid, else regular price."""
        if self.sale_price and self.sale_price < self.price:
            return self.sale_price
        return self.price

    @property
    def is_on_sale(self):
        return bool(self.sale_price and self.sale_price < self.price)

    @property
    def discount_percent(self):
        if not self.is_on_sale:
            return 0
        return round(((self.price - self.sale_price) / self.price) * 100)

    @property
    def in_stock(self):
        try:
            return self.inventory.is_in_stock
        except Exception:
            return False


class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False, db_index=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_images"
        ordering = ["-is_primary", "sort_order"]
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"

    def __str__(self):
        return f"{self.product.name} — Image {self.sort_order}"

    def save(self, *args, **kwargs):
        # If marked primary, unset all other primary images for this product
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class ProductSpecification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="specifications")
    key = models.CharField(max_length=200)
    value = models.CharField(max_length=500)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "product_specifications"
        ordering = ["sort_order", "key"]
        verbose_name = "Specification"
        verbose_name_plural = "Specifications"

    def __str__(self):
        return f"{self.product.name}: {self.key} = {self.value}"


class ProductVariant(models.Model):
    """
    Handles products that come in multiple options.
    e.g. guitar colour (Sunburst, Black), keyboard size (61-key, 88-key)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=200, help_text='e.g. "Color", "Size"')
    value = models.CharField(max_length=200, help_text='e.g. "Sunburst", "88-key"')
    sku_suffix = models.CharField(max_length=50)
    price_delta = models.IntegerField(
        default=0, help_text="Price difference from base price in KES (+/-)"
    )
    image = models.ImageField(upload_to="variants/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_variants"
        ordering = ["name", "value"]
        verbose_name = "Variant"
        verbose_name_plural = "Variants"

    def __str__(self):
        return f"{self.product.name} — {self.name}: {self.value}"

    @property
    def effective_price(self):
        return self.product.effective_price + self.price_delta