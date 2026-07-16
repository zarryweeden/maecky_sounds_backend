import logging
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .cookies import set_auth_cookies, clear_auth_cookies
from .models import Address
from .serializers import (
    SignupSerializer,
    LoginSerializer,
    UserProfileSerializer,
    AddressSerializer,
    ChangePasswordSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class AuthRateThrottle(AnonRateThrottle):
    rate = "10/minute"


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return refresh, refresh.access_token


def build_auth_response(user, status_code=status.HTTP_200_OK):
    refresh, access = get_tokens_for_user(user)
    serializer = UserProfileSerializer(user)
    response = Response(
        {
            "status": "success",
            "user": serializer.data,
            "access_token": str(access),
        },
        status=status_code,
    )
    set_auth_cookies(response, access, refresh)
    return response


class SignupView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return build_auth_response(user, status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        if not user:
            return Response(
                {"status": "error", "message": "Invalid email or password. Please try again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"status": "error", "message": "This account has been deactivated. Please contact support."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])
        return build_auth_response(user)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"])
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        response = Response(
            {"status": "success", "message": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )
        clear_auth_cookies(response)
        return response


class TokenRefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"])
        if not refresh_token:
            return Response(
                {"status": "error", "message": "Refresh token not found."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(refresh_token)
            access = refresh.access_token
            user_id = refresh.payload.get("user_id")
            user = User.objects.get(id=user_id)

            response = Response(
                {
                    "status": "success",
                    "user": UserProfileSerializer(user).data,
                    "access_token": str(access),
                },
                status=status.HTTP_200_OK,
            )
            set_auth_cookies(response, access, refresh)
            return response

        except (TokenError, User.DoesNotExist):
            response = Response(
                {"status": "error", "message": "Session expired. Please sign in again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            clear_auth_cookies(response)
            return response


class SessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "status": "success",
                "user": UserProfileSerializer(request.user).data,
            }
        )


class GoogleFinishView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.shortcuts import redirect
        if not request.user.is_authenticated:
            return redirect(f"{settings.FRONTEND_URL}/login?error=google_failed")

        refresh, access = get_tokens_for_user(request.user)
        response = redirect(f"{settings.FRONTEND_URL}/account")
        set_auth_cookies(response, access, refresh)
        return response


class NewsletterSubscribeView(APIView):
    """
    Lightweight newsletter subscription endpoint.
    For authenticated users: updates their profile.
    For guests: just records the email (could integrate with Mailchimp etc).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email or "@" not in email:
            return Response(
                {"status": "error", "message": "A valid email address is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user.is_authenticated:
            request.user.newsletter_subscribed = True
            request.user.save(update_fields=["newsletter_subscribed"])

        # Log it — in production you'd push to Mailchimp/SendGrid here
        logger.info(f"Newsletter subscription: {email}")

        return Response(
            {"status": "success", "message": "Successfully subscribed to the Maecky Sounds newsletter!"}
        )


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"status": "error", "message": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE_REFRESH"])
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        return build_auth_response(user)


class PasswordResetView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
            from apps.notifications.tasks import send_password_reset_email
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"
            send_password_reset_email.delay(str(user.id), reset_url)
        except User.DoesNotExist:
            pass  # Never reveal whether the email exists

        return Response(
            {
                "status": "success",
                "message": "If an account exists with this email, a password reset link has been sent.",
            }
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str

        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, User.DoesNotExist):
            return Response(
                {"status": "error", "message": "Invalid password reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, serializer.validated_data["token"]):
            return Response(
                {"status": "error", "message": "This password reset link has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"status": "success", "message": "Password reset successfully. You can now sign in."})


# ── Profile Views ─────────────────────────────────────────────────────────────

class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


class AvatarUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if "avatar" not in request.FILES:
            return Response(
                {"status": "error", "message": "No image file was provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES["avatar"]
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if file.content_type not in allowed_types:
            return Response(
                {"status": "error", "message": "Please upload a JPEG, PNG, or WebP image."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file.size > 5 * 1024 * 1024:
            return Response(
                {"status": "error", "message": "Image must be smaller than 5MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if user.avatar:
            user.avatar.delete(save=False)

        user.avatar = file
        user.save(update_fields=["avatar"])

        return Response(
            {
                "status": "success",
                "avatar": request.build_absolute_uri(user.avatar.url),
            }
        )


# ── Address Views ─────────────────────────────────────────────────────────────

class AddressListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        is_first = not Address.objects.filter(user=self.request.user).exists()
        serializer.save(user=self.request.user, is_default=is_first)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


class SetDefaultAddressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            address = Address.objects.get(pk=pk, user=request.user)
        except Address.DoesNotExist:
            return Response(
                {"status": "error", "message": "Address not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
        address.is_default = True
        address.save(update_fields=["is_default"])

        return Response(
            {
                "status": "success",
                "message": "Default address updated.",
                "address": AddressSerializer(address).data,
            }
        )