# FILE: feature_flags/admin.py
# UPDATED FILE

from django.contrib import admin
from .models import FeatureFlag, UserIdentifier, Experiment, Variant, Assignment


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "rollout_percentage", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]


@admin.register(UserIdentifier)
class UserIdentifierAdmin(admin.ModelAdmin):
    list_display = ["external_id", "created_at"]
    search_fields = ["external_id"]


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ["name", "feature_flag", "status", "created_at"]
    list_filter = ["status"]


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ["name", "experiment", "weight"]


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ["user", "experiment", "variant", "created_at"]