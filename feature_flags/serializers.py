# FILE: feature_flags/serializers.py
# UPDATED FILE

from rest_framework import serializers
from .models import FeatureFlag, Experiment, Variant, Assignment, UserIdentifier


# ── Phase 3 serializers (unchanged) ──────────────────────────────

class EvaluateFlagSerializer(serializers.Serializer):
    flag_name = serializers.SlugField(max_length=100)
    user_id = serializers.CharField(max_length=255)


class FeatureFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlag
        fields = [
            "id", "name", "description",
            "is_active", "rollout_percentage",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ── Phase 4 serializers (new) ─────────────────────────────────────

class VariantSerializer(serializers.ModelSerializer):
    """
    Serializes a Variant for create/read.
    """
    class Meta:
        model = Variant
        fields = ["id", "name", "weight", "created_at"]
        read_only_fields = ["id", "created_at"]


class ExperimentSerializer(serializers.ModelSerializer):
    """
    Serializes an Experiment.
    Includes nested variants on read (read_only).
    Accepts feature_flag by ID on write.
    """
    variants = VariantSerializer(many=True, read_only=True)

    class Meta:
        model = Experiment
        fields = [
            "id", "name", "description",
            "feature_flag", "status",
            "variants",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "variants", "created_at", "updated_at"]


class AssignUserSerializer(serializers.Serializer):
    """
    Validates the request body for POST /api/experiments/assign/
    """
    experiment_id = serializers.IntegerField()
    user_id = serializers.CharField(max_length=255)


class AssignmentSerializer(serializers.ModelSerializer):
    """
    Serializes an Assignment for read responses.
    """
    user = serializers.CharField(source="user.external_id")
    experiment = serializers.CharField(source="experiment.name")
    variant = serializers.CharField(source="variant.name")

    class Meta:
        model = Assignment
        fields = ["id", "user", "experiment", "variant", "created_at"]
        read_only_fields = ["id", "created_at"]