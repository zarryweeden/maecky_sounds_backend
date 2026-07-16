from django.urls import path
from apps.users.views import (
    SignupView,
    LoginView,
    LogoutView,
    TokenRefreshView,
    SessionView,
    GoogleFinishView,
    NewsletterSubscribeView,
    ChangePasswordView,
    PasswordResetView,
    PasswordResetConfirmView,
)

urlpatterns = [
    path("signup/", SignupView.as_view(), name="auth-signup"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("session/", SessionView.as_view(), name="auth-session"),
    path("google/finish/", GoogleFinishView.as_view(), name="auth-google-finish"),
    path("newsletter/", NewsletterSubscribeView.as_view(), name="auth-newsletter"),
    path("password/change/", ChangePasswordView.as_view(), name="auth-password-change"),
    path("password/reset/", PasswordResetView.as_view(), name="auth-password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
]