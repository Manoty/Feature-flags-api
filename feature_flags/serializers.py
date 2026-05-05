# FILE: feature_flags/serializers.py
# UPDATED FILE

from rest_framework import serializers
from .models import FeatureFlag, Experiment, Variant, Assignment, MetricEvent


# ── Phase 3 ───────────────────────────────────────────────────────

class EvaluateFlagSerializer(serializers.Serializer):
    flag_name = serializers.SlugField(max_length=100)
    user_id = serializers.CharField(max_length=255)


class FeatureFlagSerializer(serializers.ModelSerializer):

    def validate_rollout_percentage(self, value):
        if not (0 <= value <= 100):
            raise serializers.ValidationError("Must be between 0 and 100.")
        return value

    def validate_name(self, value):
        if not value.replace("-", "").replace("_", "").isalnum():
            raise serializers.ValidationError(
                "Name must contain only letters, numbers, hyphens, and underscores."
            )
        return value

    class Meta:
        model = FeatureFlag
        fields = [
            "id", "name", "description",
            "is_active", "rollout_percentage",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ── Phase 4 ───────────────────────────────────────────────────────

class VariantSerializer(serializers.ModelSerializer):

    def validate_weight(self, value):
        if value < 1:
            raise serializers.ValidationError("Weight must be at least 1.")
        return value

    class Meta:
        model = Variant
        fields = ["id", "name", "weight", "created_at"]
        read_only_fields = ["id", "created_at"]


class ExperimentSerializer(serializers.ModelSerializer):
    variants = VariantSerializer(many=True, read_only=True)

    def validate_status(self, value):
        """
        On update: block reverting a completed experiment to running.
        """
        if self.instance:
            if (
                self.instance.status == Experiment.Status.COMPLETED
                and value == Experiment.Status.RUNNING
            ):
                raise serializers.ValidationError(
                    "A completed experiment cannot be set back to running."
                )
        return value

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
    experiment_id = serializers.IntegerField(min_value=1)
    user_id = serializers.CharField(max_length=255)


class AssignmentSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.external_id")
    experiment = serializers.CharField(source="experiment.name")
    variant = serializers.CharField(source="variant.name")

    class Meta:
        model = Assignment
        fields = ["id", "user", "experiment", "variant", "created_at"]
        read_only_fields = ["id", "created_at"]


# ── Phase 5 ───────────────────────────────────────────────────────

class LogEventSerializer(serializers.Serializer):
    experiment_id = serializers.IntegerField(min_value=1)
    user_id = serializers.CharField(max_length=255)
    event_type = serializers.ChoiceField(
        choices=MetricEvent.EventType.choices
    )