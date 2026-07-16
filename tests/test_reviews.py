import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.products.models import Product, Category, Brand
from apps.inventory.models import Inventory
from apps.reviews.models import Review

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="reviewer@maeckysounds.co.ke",
        password="ReviewPass123!",
        full_name="Test Reviewer",
    )


@pytest.fixture
def auth_client(client, user):
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def product(db):
    category = Category.objects.create(name="Guitars Rev", slug="guitars-reviews-test", is_active=True)
    brand = Brand.objects.create(name="Yamaha Rev", slug="yamaha-reviews-test", is_active=True)
    p = Product.objects.create(
        sku="REV-TEST-001",
        name="Review Test Guitar",
        slug="review-test-guitar",
        brand=brand,
        category=category,
        price=40000,
        is_active=True,
        average_rating=0,
        review_count=0,
    )
    Inventory.objects.create(product=p, quantity=5)
    return p


@pytest.mark.django_db
class TestReviews:
    def test_create_review_succeeds(self, auth_client, product):
        url = reverse("product-reviews", kwargs={"slug": product.slug})
        response = auth_client.post(url, {
            "rating": 5,
            "title": "Great guitar!",
            "body": "This guitar exceeded my expectations in every way. Highly recommend!",
        }, format="json")

        assert response.status_code == 201
        assert Review.objects.filter(product=product).count() == 1

    def test_can_only_review_once_per_product(self, auth_client, user, product):
        Review.objects.create(
            product=product,
            user=user,
            rating=4,
            body="My initial review — solid build quality overall.",
        )
        url = reverse("product-reviews", kwargs={"slug": product.slug})
        response = auth_client.post(url, {
            "rating": 5,
            "body": "Another review attempt — but I already reviewed.",
        }, format="json")

        assert response.status_code == 400

    def test_review_updates_product_average_rating(self, auth_client, product):
        url = reverse("product-reviews", kwargs={"slug": product.slug})
        auth_client.post(url, {
            "rating": 4,
            "body": "Really solid instrument at this price point. Impressed.",
        }, format="json")

        product.refresh_from_db()
        assert product.average_rating == 4.0
        assert product.review_count == 1

    def test_review_requires_minimum_body_length(self, auth_client, product):
        url = reverse("product-reviews", kwargs={"slug": product.slug})
        response = auth_client.post(url, {
            "rating": 3,
            "body": "Short",
        }, format="json")

        assert response.status_code == 400

    def test_review_requires_authentication(self, client, product):
        url = reverse("product-reviews", kwargs={"slug": product.slug})
        response = client.post(url, {
            "rating": 5,
            "body": "This should not be allowed without logging in.",
        }, format="json")

        assert response.status_code == 401

    def test_get_reviews_is_public(self, client, product):
        url = reverse("product-reviews", kwargs={"slug": product.slug})
        response = client.get(url)

        assert response.status_code == 200

    def test_review_summary_returns_correct_structure(self, client, product):
        url = reverse("review-summary", kwargs={"slug": product.slug})
        response = client.get(url)

        assert response.status_code == 200
        assert "average_rating" in response.data
        assert "review_count" in response.data
        assert "rating_distribution" in response.data
        assert "verified_count" in response.data