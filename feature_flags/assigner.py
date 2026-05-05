# FILE: feature_flags/assigner.py
# NEW FILE

import hashlib
from .models import Experiment, Variant, UserIdentifier, Assignment


def get_assignment_bucket(user_id: str, experiment_id: int) -> int:
    """
    Deterministically assign user to bucket 0–99.

    Combines user_id + experiment_id so that:
    - Same user → same bucket for this experiment, always
    - Bucket is independent per experiment (user_001 may be
      bucket 12 in experiment 1 but bucket 67 in experiment 2)
    """
    raw = f"{user_id}{experiment_id}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:8], 16) % 100


def pick_variant_by_weight(variants, bucket: int):
    """
    Given a list of Variant objects and a bucket (0–99),
    pick which variant the user falls into based on weights.

    Example:
        control   weight=50 → covers buckets 0–49
        treatment weight=50 → covers buckets 50–99

        bucket=23 → control
        bucket=74 → treatment

    Weights don't need to sum to 100 — we normalize them.
    """
    total_weight = sum(v.weight for v in variants)
    if total_weight == 0:
        return variants[0]  # fallback: return first variant

    # Scale bucket into total weight range
    scaled = (bucket / 100) * total_weight
    cumulative = 0

    for variant in variants:
        cumulative += variant.weight
        if scaled < cumulative:
            return variant

    return variants[-1]  # safety fallback


def assign_user(experiment_id: int, user_id: str) -> dict:
    """
    Core assignment engine.

    Returns a dict describing the assignment result.
    Never raises — always returns a safe response dict.
    """

    # ── Rule 1: Does the experiment exist? ────────────────────────
    try:
        experiment = Experiment.objects.prefetch_related("variants").get(
            id=experiment_id
        )
    except Experiment.DoesNotExist:
        return {
            "success": False,
            "error": "experiment_not_found",
            "experiment_id": experiment_id,
            "user_id": user_id,
        }

    # ── Rule 2: Is the experiment running? ────────────────────────
    if experiment.status != Experiment.Status.RUNNING:
        return {
            "success": False,
            "error": "experiment_not_running",
            "experiment_id": experiment_id,
            "status": experiment.status,
            "user_id": user_id,
        }

    # ── Rule 3: Does the experiment have variants? ────────────────
    variants = list(experiment.variants.all())
    if not variants:
        return {
            "success": False,
            "error": "no_variants_defined",
            "experiment_id": experiment_id,
            "user_id": user_id,
        }

    # ── Rule 4: Already assigned? Return existing ─────────────────
    user, _ = UserIdentifier.objects.get_or_create(external_id=user_id)

    existing = Assignment.objects.filter(
        user=user,
        experiment=experiment
    ).select_related("variant").first()

    if existing:
        return {
            "success": True,
            "already_assigned": True,
            "user_id": user_id,
            "experiment_id": experiment.id,
            "experiment_name": experiment.name,
            "variant_id": existing.variant.id,
            "variant_name": existing.variant.name,
        }

    # ── Rule 5: Hash → pick variant → save ───────────────────────
    bucket = get_assignment_bucket(user_id, experiment_id)
    variant = pick_variant_by_weight(variants, bucket)

    assignment = Assignment.objects.create(
        user=user,
        experiment=experiment,
        variant=variant,
    )

    return {
        "success": True,
        "already_assigned": False,
        "user_id": user_id,
        "experiment_id": experiment.id,
        "experiment_name": experiment.name,
        "variant_id": variant.id,
        "variant_name": variant.name,
        "bucket": bucket,  # useful for debugging
    }