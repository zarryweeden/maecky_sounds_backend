import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.products.models import Product, Category, Brand
from apps.inventory.models import Inventory
from apps.orders.models import Cart, CartItem, Order

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="buyer@maeckysounds.co.ke",
        password="BuyerPass123!",
        full_name="Test Buyer",
        phone="0712345678",
    )


@pytest.fixture
def auth_client(client, user):
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def product(db):
    category = Category.objects.create(name="Guitars", slug="guitars-orders-test", is_active=True)
    brand = Brand.objects.create(name="Fender", slug="fender-orders-test", is_active=True)
    p = Product.objects.create(
        sku="ORD-TEST-001",
        name="Order Test Guitar",
        slug="order-test-guitar",
        brand=brand,
        category=category,
        price=50000,
        is_active=True,
    )
    Inventory.objects.create(product=p, quantity=10, track_inventory=True)
    return p


@pytest.fixture
def cart_with_item(db, user, product):
    cart = Cart.objects.create(user=user, is_active=True)
    CartItem.objects.create(
        cart=cart,
        product=product,
        quantity=1,
        unit_price=product.effective_price,
    )
    return cart


@pytest.mark.django_db
class TestCart:
    def test_get_cart_returns_empty_cart(self, auth_client):
        url = reverse("cart-detail")
        response = auth_client.get(url)

        assert response.status_code == 200
        assert "items" in response.data

    def test_add_item_to_cart(self, auth_client, product):
        url = reverse("cart-add-item")
        response = auth_client.post(url, {
            "product_id": str(product.id),
            "quantity": 1,
        }, format="json")

        assert response.status_code == 201
        assert len(response.data["items"]) == 1

    def test_add_item_exceeding_stock_fails(self, auth_client, product):
        url = reverse("cart-add-item")
        response = auth_client.post(url, {
            "product_id": str(product.id),
            "quantity": 999,
        }, format="json")

        assert response.status_code == 400

    def test_apply_coupon_to_cart(self, auth_client, cart_with_item):
        from apps.coupons.models import Coupon
        from django.utils import timezone

        Coupon.objects.create(
            code="TEST10",
            discount_type=Coupon.DiscountType.PERCENTAGE,
            discount_value=10,
            valid_from=timezone.now(),
            is_active=True,
        )

        url = reverse("cart-apply-coupon")
        response = auth_client.post(url, {"code": "TEST10"}, format="json")

        assert response.status_code == 200
        assert response.data["status"] == "success"

    def test_clear_cart(self, auth_client, cart_with_item):
        url = reverse("cart-clear")
        response = auth_client.delete(url)

        assert response.status_code == 200
        assert len(response.data.get("items", [])) == 0


@pytest.mark.django_db
class TestOrderPlacement:
    def test_place_order_creates_order_and_reserves_inventory(
        self, auth_client, cart_with_item, product
    ):
        url = reverse("order-place")
        response = auth_client.post(url, {
            "delivery_method": "standard",
            "payment_method": "mpesa",
            "shipping_address": {
                "full_name": "Test Buyer",
                "phone": "0712345678",
                "address_line1": "123 Test Street",
                "city": "Nairobi",
                "county": "Nairobi County",
            },
        }, format="json")

        assert response.status_code == 201
        assert "order" in response.data
        assert response.data["order"]["status"] == "pending"

        product.inventory.refresh_from_db()
        assert product.inventory.reserved == 1

    def test_place_order_fails_with_empty_cart(self, auth_client):
        url = reverse("order-place")
        response = auth_client.post(url, {
            "delivery_method": "standard",
            "payment_method": "mpesa",
            "shipping_address": {
                "full_name": "Test Buyer",
                "phone": "0712345678",
                "address_line1": "123 Test Street",
                "city": "Nairobi",
                "county": "Nairobi County",
            },
        }, format="json")

        assert response.status_code == 400

    def test_place_order_requires_authentication(self, client, cart_with_item):
        url = reverse("order-place")
        response = client.post(url, {
            "delivery_method": "standard",
            "payment_method": "mpesa",
            "shipping_address": {},
        }, format="json")

        assert response.status_code == 401

    def test_order_list_only_shows_own_orders(self, auth_client, user):
        other_user = User.objects.create_user(
            email="other@maeckysounds.co.ke",
            password="OtherPass123!",
        )
        Order.objects.create(
            user=other_user,
            subtotal=50000,
            total=50000,
            delivery_method="standard",
            shipping_address={},
            customer_email=other_user.email,
            customer_name="Other User",
            customer_phone="0799999999",
        )

        url = reverse("order-list")
        response = auth_client.get(url)

        assert response.status_code == 200
        for order in response.data["results"]:
            assert order["customer_email"] != other_user.email


@pytest.mark.django_db
class TestOrderCancellation:
    def test_cancel_pending_order_releases_inventory(
        self, auth_client, cart_with_item, product
    ):
        # Place order first
        place_url = reverse("order-place")
        place_resp = auth_client.post(place_url, {
            "delivery_method": "standard",
            "payment_method": "mpesa",
            "shipping_address": {
                "full_name": "Test Buyer",
                "phone": "0712345678",
                "address_line1": "123 Test Street",
                "city": "Nairobi",
                "county": "Nairobi County",
            },
        }, format="json")

        assert place_resp.status_code == 201
        order_number = place_resp.data["order"]["order_number"]

        # Cancel it
        cancel_url = reverse("order-cancel", kwargs={"order_number": order_number})
        cancel_resp = auth_client.post(cancel_url)

        assert cancel_resp.status_code == 200
        assert cancel_resp.data["order"]["status"] == "cancelled"

        product.inventory.refresh_from_db()
        assert product.inventory.reserved == 0