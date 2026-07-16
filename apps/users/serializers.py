import re
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import Address

User = get_user_model()


def validate_kenyan_phone(value):
    """Validate and normalise Kenyan phone numbers."""
    if not value:
        return value
    cleaned = re.sub(r"[\s\-\(\)]", "", value)
    patterns = [
        r"^\+2547\d{8}$",
        r"^\+2541\d{8}$",
        r"^07\d{8}$",
        r"^01\d{8}$",
        r"^2547\d{8}$",
    ]
    if not any(re.match(p, cleaned) for p in patterns):
        raise serializers.ValidationError(
            "Please enter a valid Kenyan phone number (e.g. 0712345678 or +254712345678)."
        )
    return cleaned


class UserMiniSerializer(serializers.ModelSerializer):
    """Minimal user info for embedding in other serializers."""

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "avatar"]
        read_only_fields = fields


class UserProfileSerializer(serializers.ModelSerializer):
    """Full user profile for /users/me/ endpoint."""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "avatar",
            "email_verified",
            "newsletter_subscribed",
            "marketing_emails",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "email", "email_verified", "date_joined", "last_login"]

    def validate_phone(self, value):
        return validate_kenyan_phone(value)

    def validate_full_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError("Full name must be at least 2 characters.")
        return value.strip()


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        error_messages={"min_length": "Password must be at least 8 characters long."},
    )
    password2 = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ["full_name", "email", "password", "password2"]

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                "An account with this email address already exists."
            )
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data.get("full_name", ""),
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        error_messages={"required": "Email address is required to sign in."}
    )
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        error_messages={"required": "Password is required to sign in."},
    )

    def validate_email(self, value):
        return value.lower().strip()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        error_messages={"min_length": "New password must be at least 8 characters long."},
    )
    new_password2 = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "New passwords do not match."})
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower().strip()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    uid = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )
    new_password2 = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "Passwords do not match."})
        return attrs


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "label",
            "full_name",
            "phone",
            "address_line1",
            "address_line2",
            "city",
            "county",
            "postal_code",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_phone(self, value):
        return validate_kenyan_phone(value)

    def validate_full_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Full name must be at least 2 characters.")
        return value.strip()