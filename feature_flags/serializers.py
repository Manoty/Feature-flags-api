from rest_framework import serializers
from .models import FeatureFlag


class EvaluateFlagSerializer(serializers.Serializer):
    """
    Validates the request body for POST /api/flags/evaluate/
    """
    flag_name = serializers.SlugField(
        max_length=100,
        help_text="The flag name e.g. 'dark-mode'"
    )
    user_id = serializers.CharField(
        max_length=255,
        help_text="Your system's user identifier e.g. 'user_001'"
    )


class FeatureFlagSerializer(serializers.ModelSerializer):
    """
    Serializes a FeatureFlag for create/read responses.
    """
    class Meta:
        model = FeatureFlag
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "rollout_percentage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]