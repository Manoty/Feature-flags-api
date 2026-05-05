# FILE: feature_flags/models.py
# UPDATED FILE

from django.db import models


# ─────────────────────────────────────────
# BASE MODEL
# Gives every model created_at + updated_at
# ─────────────────────────────────────────

class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True  # never creates its own table


# ─────────────────────────────────────────
# FEATURE FLAG
# The core toggle. Represents one feature.
# ─────────────────────────────────────────

class FeatureFlag(TimestampedModel):
    name = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Unique identifier e.g. 'dark-mode', 'new-checkout'"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(
        default=False,
        help_text="Global kill switch. False = off for everyone."
    )
    rollout_percentage = models.PositiveSmallIntegerField(
        default=100,
        help_text="0–100. What % of users see this flag when active."
    )

    def __str__(self):
        return f"{self.name} ({'on' if self.is_active else 'off'})"

    class Meta:
        db_table = "feature_flags"
        ordering = ["name"]


# ─────────────────────────────────────────
# USER IDENTIFIER
# Lightweight user record. No auth needed.
# external_id comes from your own system.
# ─────────────────────────────────────────

class UserIdentifier(TimestampedModel):
    external_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="ID from your system: UUID, user_123, hashed email, etc."
    )

    def __str__(self):
        return self.external_id

    class Meta:
        db_table = "user_identifiers"


# ─────────────────────────────────────────
# EXPERIMENT
# A named A/B test linked to a feature flag.
# One flag → one experiment.
# ─────────────────────────────────────────

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
        help_text="Each flag can have at most one experiment."
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


# ─────────────────────────────────────────
# VARIANT
# A bucket inside an experiment.
# e.g. "control" (weight 50) + "treatment" (weight 50)
# weight is relative — doesn't need to sum to 100.
# ─────────────────────────────────────────

class Variant(TimestampedModel):
    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    name = models.CharField(
        max_length=100,
        help_text="e.g. 'control', 'treatment', 'variant-b'"
    )
    weight = models.PositiveSmallIntegerField(
        default=50,
        help_text="Relative weight for assignment. control=50, treatment=50 → 50/50 split."
    )

    def __str__(self):
        return f"{self.experiment.name} → {self.name}"

    class Meta:
        db_table = "variants"
        unique_together = [("experiment", "name")]  # no duplicate variant names per experiment


# ─────────────────────────────────────────
# ASSIGNMENT
# Records which variant a user was put in.
# unique_together ensures one variant per user per experiment.
# ─────────────────────────────────────────

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
        unique_together = [("user", "experiment")]  # DB-enforced: one variant per user per experiment