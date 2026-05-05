# FILE: feature_flags/models.py
# UPDATED FILE

from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db import models


# ── Base Model ────────────────────────────────────────────────────

class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ── Feature Flag ──────────────────────────────────────────────────

class FeatureFlag(TimestampedModel):
    name = models.SlugField(
        max_length=100,
        unique=True,
        db_index=True,               # explicit — this is our primary lookup field
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=False)
    rollout_percentage = models.PositiveSmallIntegerField(
        default=100,
        validators=[
            MinValueValidator(0, message="Rollout percentage cannot be negative."),
            MaxValueValidator(100, message="Rollout percentage cannot exceed 100."),
        ]
    )

    def clean(self):
        """
        Model-level validation.
        Called by full_clean() — runs in admin and anywhere
        you call instance.full_clean() before saving.
        """
        if self.rollout_percentage is not None:
            if not (0 <= self.rollout_percentage <= 100):
                raise ValidationError({
                    "rollout_percentage": "Must be between 0 and 100."
                })

    def __str__(self):
        return f"{self.name} ({'on' if self.is_active else 'off'})"

    class Meta:
        db_table = "feature_flags"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="idx_flag_name"),
            models.Index(fields=["is_active"], name="idx_flag_active"),
        ]


# ── User Identifier ───────────────────────────────────────────────

class UserIdentifier(TimestampedModel):
    external_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,               # looked up on every assignment + event
    )

    def __str__(self):
        return self.external_id

    class Meta:
        db_table = "user_identifiers"
        indexes = [
            models.Index(fields=["external_id"], name="idx_user_external_id"),
        ]


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

    def clean(self):
        """
        Prevent setting a paused/completed experiment back to running
        without going through draft first — protects data integrity.
        """
        if self.pk:  # only on update, not create
            try:
                old = Experiment.objects.get(pk=self.pk)
                if old.status == Experiment.Status.COMPLETED and self.status == Experiment.Status.RUNNING:
                    raise ValidationError({
                        "status": "A completed experiment cannot be set back to running."
                    })
            except Experiment.DoesNotExist:
                pass

    def __str__(self):
        return f"{self.name} [{self.status}]"

    class Meta:
        db_table = "experiments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="idx_experiment_status"),
            models.Index(fields=["feature_flag"], name="idx_experiment_flag"),
        ]


# ── Variant ───────────────────────────────────────────────────────

class Variant(TimestampedModel):
    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    name = models.CharField(max_length=100)
    weight = models.PositiveSmallIntegerField(
        default=50,
        validators=[
            MinValueValidator(1, message="Weight must be at least 1."),
        ]
    )

    def __str__(self):
        return f"{self.experiment.name} → {self.name}"

    class Meta:
        db_table = "variants"
        unique_together = [("experiment", "name")]
        indexes = [
            models.Index(fields=["experiment"], name="idx_variant_experiment"),
        ]


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
        indexes = [
            models.Index(fields=["user", "experiment"], name="idx_assignment_user_exp"),
        ]


# ── Metric Event ──────────────────────────────────────────────────

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
        unique_together = [("experiment", "variant", "user", "event_type")]
        indexes = [
            models.Index(fields=["experiment", "event_type"], name="idx_event_exp_type"),
            models.Index(fields=["variant", "event_type"], name="idx_event_variant_type"),
        ]