import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user_data():
    return {
        "full_name": "Test User",
        "email": "test@maeckysounds.co.ke",
        "password": "SecurePass123!",
        "password2": "SecurePass123!",
    }


@pytest.fixture
def existing_user(db):
    return User.objects.create_user(
        email="existing@maeckysounds.co.ke",
        password="SecurePass123!",
        full_name="Existing User",
    )


@pytest.mark.django_db
class TestSignup:
    def test_signup_creates_user_and_sets_cookies(self, client, user_data):
        url = reverse("auth-signup")
        response = client.post(url, user_data, format="json")

        assert response.status_code == 201
        assert "user" in response.data
        assert response.data["user"]["email"] == user_data["email"]
        assert "ms_access" in response.cookies
        assert "ms_refresh" in response.cookies
        assert User.objects.filter(email=user_data["email"]).exists()

    def test_signup_duplicate_email_returns_400(self, client, user_data, existing_user):
        user_data["email"] = existing_user.email
        url = reverse("auth-signup")
        response = client.post(url, user_data, format="json")

        assert response.status_code == 400

    def test_signup_password_mismatch_returns_400(self, client, user_data):
        user_data["password2"] = "DifferentPassword!"
        url = reverse("auth-signup")
        response = client.post(url, user_data, format="json")

        assert response.status_code == 400

    def test_signup_weak_password_returns_400(self, client, user_data):
        user_data["password"] = "123"
        user_data["password2"] = "123"
        url = reverse("auth-signup")
        response = client.post(url, user_data, format="json")

        assert response.status_code == 400


@pytest.mark.django_db
class TestLogin:
    def test_login_success_returns_user_and_cookies(self, client, existing_user):
        url = reverse("auth-login")
        response = client.post(url, {
            "email": existing_user.email,
            "password": "SecurePass123!",
        }, format="json")

        assert response.status_code == 200
        assert response.data["user"]["email"] == existing_user.email
        assert "ms_access" in response.cookies
        assert "ms_refresh" in response.cookies

    def test_login_wrong_password_returns_401(self, client, existing_user):
        url = reverse("auth-login")
        response = client.post(url, {
            "email": existing_user.email,
            "password": "WrongPassword!",
        }, format="json")

        assert response.status_code == 401

    def test_login_nonexistent_email_returns_401(self, client):
        url = reverse("auth-login")
        response = client.post(url, {
            "email": "nobody@nowhere.com",
            "password": "SomePassword123!",
        }, format="json")

        assert response.status_code == 401

    def test_login_inactive_user_returns_403(self, client, existing_user):
        existing_user.is_active = False
        existing_user.save()

        url = reverse("auth-login")
        response = client.post(url, {
            "email": existing_user.email,
            "password": "SecurePass123!",
        }, format="json")

        assert response.status_code == 403


@pytest.mark.django_db
class TestSession:
    def test_session_returns_user_when_authenticated(self, client, existing_user):
        client.force_authenticate(user=existing_user)
        url = reverse("auth-session")
        response = client.get(url)

        assert response.status_code == 200
        assert response.data["user"]["email"] == existing_user.email

    def test_session_returns_401_when_unauthenticated(self, client):
        url = reverse("auth-session")
        response = client.get(url)

        assert response.status_code == 401


@pytest.mark.django_db
class TestLogout:
    def test_logout_clears_cookies(self, client, existing_user):
        client.force_authenticate(user=existing_user)
        url = reverse("auth-logout")
        response = client.post(url)

        assert response.status_code == 200
        assert response.data["status"] == "success"