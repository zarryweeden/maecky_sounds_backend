from rest_framework import serializers
from .models import Review, ReviewHelpful


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "user_name",
            "user_avatar",
            "rating",
            "title",
            "body",
            "is_verified",
            "helpful_count",
            "unhelpful_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "user_name", "user_avatar",
            "is_verified", "helpful_count", "unhelpful_count",
            "created_at", "updated_at",
        ]

    def get_user_name(self, obj):
        name = obj.user.full_name or obj.user.email
        # Partially mask for privacy: "John K." or "jo***@email.com"
        if obj.user.full_name:
            parts = obj.user.full_name.strip().split()
            if len(parts) >= 2:
                return f"{parts[0]} {parts[-1][0]}."
            return parts[0]
        return obj.user.email[:3] + "***"

    def get_user_avatar(self, obj):
        request = self.context.get("request")
        if obj.user.avatar:
            if request:
                return request.build_absolute_uri(obj.user.avatar.url)
            return obj.user.avatar.url
        return None


class CreateReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["rating", "title", "body"]

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_body(self, value):
        if len(value.strip()) < 20:
            raise serializers.ValidationError(
                "Review must be at least 20 characters long."
            )
        return value.strip()

    def validate_title(self, value):
        return value.strip()


class ReviewSummarySerializer(serializers.Serializer):
    """Rating breakdown for a product."""
    average_rating = serializers.FloatField()
    review_count = serializers.IntegerField()
    rating_distribution = serializers.DictField(child=serializers.IntegerField())
    verified_count = serializers.IntegerField()