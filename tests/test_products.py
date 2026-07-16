import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.products.models import Product, Category, Brand
from apps.inventory.models import Inventory


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def category(db):
    return Category.objects.create(name="Test Guitars", slug="test-guitars", is_active=True)


@pytest.fixture
def brand(db):
    return Brand.objects.create(name="Test Brand", slug="test-brand", is_active=True)


@pytest.fixture
def product(db, category, brand):
    p = Product.objects.create(
        sku="TEST-001",
        name="Test Guitar",
        slug="test-guitar",
        brand=brand,
        category=category,
        price=50000,
        is_active=True,
        is_featured=True,
        is_new=True,
    )
    Inventory.objects.create(product=p, quantity=10, track_inventory=True)
    return p


@pytest.fixture
def sale_product(db, category, brand):
    p = Product.objects.create(
        sku="TEST-SALE-001",
        name="Sale Guitar",
        slug="sale-guitar",
        brand=brand,
        category=category,
        price=100000,
        sale_price=75000,
        is_active=True,
    )
    Inventory.objects.create(product=p, quantity=5, track_inventory=True)
    return p


@pytest.mark.django_db
class TestProductList:
    def test_product_list_returns_paginated_results(self, client, product):
        url = reverse("product-list")
        response = client.get(url)

        assert response.status_code == 200
        assert "results" in response.data
        assert "count" in response.data
        assert response.data["count"] >= 1

    def test_product_list_filter_by_category(self, client, product, category):
        url = reverse("product-list")
        response = client.get(url, {"category": category.slug})

        assert response.status_code == 200
        assert response.data["count"] >= 1
        for p in response.data["results"]:
            assert p["category"]["slug"] == category.slug

    def test_product_list_filter_by_price_range(self, client, product):
        url = reverse("product-list")
        response = client.get(url, {"min_price": 10000, "max_price": 80000})

        assert response.status_code == 200
        for p in response.data["results"]:
            assert p["price"] >= 10000
            assert p["price"] <= 80000

    def test_product_list_filter_in_stock(self, client, product):
        url = reverse("product-list")
        response = client.get(url, {"in_stock": "true"})

        assert response.status_code == 200
        for p in response.data["results"]:
            assert p["in_stock"] is True

    def test_product_list_filter_is_new(self, client, product):
        url = reverse("product-list")
        response = client.get(url, {"is_new": "true"})

        assert response.status_code == 200
        for p in response.data["results"]:
            assert p["is_new"] is True

    def test_product_list_filter_is_sale(self, client, sale_product):
        url = reverse("product-list")
        response = client.get(url, {"is_sale": "true"})

        assert response.status_code == 200
        for p in response.data["results"]:
            assert p["is_on_sale"] is True


@pytest.mark.django_db
class TestProductDetail:
    def test_product_detail_returns_full_data(self, client, product):
        url = reverse("product-detail", kwargs={"slug": product.slug})
        response = client.get(url)

        assert response.status_code == 200
        assert response.data["slug"] == product.slug
        assert response.data["sku"] == product.sku
        assert "inventory" in response.data
        assert "images" in response.data
        assert "specifications" in response.data

    def test_product_detail_404_for_inactive(self, client, product):
        product.is_active = False
        product.save()

        url = reverse("product-detail", kwargs={"slug": product.slug})
        response = client.get(url)

        assert response.status_code == 404

    def test_product_detail_increments_view_count(self, client, product):
        initial_views = product.view_count
        url = reverse("product-detail", kwargs={"slug": product.slug})
        client.get(url)

        product.refresh_from_db()
        assert product.view_count == initial_views + 1


@pytest.mark.django_db
class TestProductSearch:
    def test_search_finds_by_name(self, client, product):
        url = reverse("search")
        response = client.get(url, {"q": "Test Guitar"})

        assert response.status_code == 200
        assert response.data["total"] >= 1

    def test_search_finds_by_brand(self, client, product):
        url = reverse("search")
        response = client.get(url, {"q": "Test Brand"})

        assert response.status_code == 200
        assert response.data["total"] >= 1

    def test_search_empty_query_returns_empty(self, client):
        url = reverse("search")
        response = client.get(url, {"q": ""})

        assert response.status_code == 200
        assert response.data["total"] == 0

    def test_search_suggestions(self, client, product):
        url = reverse("search-suggestions")
        response = client.get(url, {"q": "Test"})

        assert response.status_code == 200
        assert "products" in response.data
        assert "categories" in response.data
        assert "brands" in response.data