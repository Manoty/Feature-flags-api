# FILE: feature_flags/models.py
# UPDATED FILE

from django.db import models


# ── Base Model ────────────────────────────────────────────────────

class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ── Feature Flag ──────────────────────────────────────────────────

class FeatureFlag(TimestampedModel):
    name = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)
    rollout_percentage = models.PositiveSmallIntegerField(default=100)

    def __str__(self):
        return f"{self.name} ({'on' if self.is_active else 'off'})"

    class Meta:
        db_table = "feature_flags"
        ordering = ["name"]


# ── User Identifier ───────────────────────────────────────────────

class UserIdentifier(TimestampedModel):
    external_id = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.external_id

    class Meta:
        db_table = "user_identifiers"


# ── Experiment ────────────────────────────────────────────────────

class Experiment(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"

    feature_flag = models.OneToOneField(
        FeatureFlag,
        on_delete=models.CASCADE,
        related_name="experiment",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    def __str__(self):
        return f"{self.name} [{self.status}]"

    class Meta:
        db_table = "experiments"
        ordering = ["-created_at"]


# ── Variant ───────────────────────────────────────────────────────

class Variant(TimestampedModel):
    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    name = models.CharField(max_length=100)
    weight = models.PositiveSmallIntegerField(default=50)

    def __str__(self):
        return f"{self.experiment.name} → {self.name}"

    class Meta:
        db_table = "variants"
        unique_together = [("experiment", "name")]


# ── Assignment ────────────────────────────────────────────────────

class Assignment(TimestampedModel):
    user = models.ForeignKey(
        UserIdentifier,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    variant = models.ForeignKey(
        Variant,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    def __str__(self):
        return f"{self.user} → {self.variant}"

    class Meta:
        db_table = "assignments"
        unique_together = [("user", "experiment")]


# ── Metric Event ──────────────────────────────────────────────────
# NEW in Phase 5
# One row per tracked event (impression or conversion).
# Raw storage — aggregate on read.

class MetricEvent(TimestampedModel):
    class EventType(models.TextChoices):
        IMPRESSION = "impression", "Impression"
        CONVERSION = "conversion", "Conversion"

    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name="events",
    )
    variant = models.ForeignKey(
        Variant,
        on_delete=models.CASCADE,
        related_name="events",
    )
    user = models.ForeignKey(
        UserIdentifier,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
    )

    def __str__(self):
        return f"{self.user} | {self.event_type} | {self.variant}"

    class Meta:
        db_table = "metric_events"
        ordering = ["-created_at"]
        # Prevent duplicate impressions/conversions per user per variant
        unique_together = [("experiment", "variant", "user", "event_type")]