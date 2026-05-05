import hashlib
from .models import FeatureFlag


def get_user_bucket(user_id: str, flag_name: str) -> int:
    """
    Deterministically assign a user to a bucket 0–99.

    Uses SHA-256 of (user_id + flag_name) so:
    - Same user + same flag → always same bucket
    - Different flags → independent bucketing (user_001 may be
      in bucket 12 for 'dark-mode' but bucket 87 for 'new-checkout')
    """
    raw = f"{user_id}{flag_name}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()  # 64-char hex string
    # Take first 8 hex chars → integer → mod 100 → bucket 0–99
    return int(digest[:8], 16) % 100


def evaluate_flag(flag_name: str, user_id: str) -> dict:
    """
    Core evaluation engine.
    Returns a dict describing whether the flag is enabled for this user.

    Never raises — always returns a safe response dict.
    """

    # ── Rule 1: Does the flag exist? ──────────────────────────────
    try:
        flag = FeatureFlag.objects.get(name=flag_name)
    except FeatureFlag.DoesNotExist:
        return {
            "enabled": False,
            "reason": "flag_not_found",
            "flag_name": flag_name,
            "user_id": user_id,
        }

    # ── Rule 2: Is the flag globally active? ─────────────────────
    if not flag.is_active:
        return {
            "enabled": False,
            "reason": "flag_disabled",
            "flag_name": flag_name,
            "user_id": user_id,
        }

    # ── Rule 3: Full rollout shortcut ────────────────────────────
    if flag.rollout_percentage >= 100:
        return {
            "enabled": True,
            "reason": "full_rollout",
            "flag_name": flag_name,
            "user_id": user_id,
        }

    # ── Rule 4: No rollout shortcut ──────────────────────────────
    if flag.rollout_percentage <= 0:
        return {
            "enabled": False,
            "reason": "zero_rollout",
            "flag_name": flag_name,
            "user_id": user_id,
        }

    # ── Rule 5: Hash-based percentage rollout ────────────────────
    bucket = get_user_bucket(user_id, flag_name)
    in_rollout = bucket < flag.rollout_percentage

    return {
        "enabled": in_rollout,
        "reason": "rollout" if in_rollout else "not_in_rollout",
        "flag_name": flag_name,
        "user_id": user_id,
        "bucket": bucket,                        # useful for debugging
        "rollout_percentage": flag.rollout_percentage,
    }