# FILE: feature_flags/evaluator.py
# UPDATED FILE

import hashlib
from django.core.cache import cache
from .models import FeatureFlag

# Cache evaluated flag configs for 60 seconds.
# Means a flag change takes up to 60s to propagate — acceptable tradeoff.
# In production swap Django's cache backend to Redis.
FLAG_CACHE_TTL = 60  # seconds


def _get_flag_cached(flag_name: str):
    """
    Fetch a FeatureFlag from cache, falling back to DB.
    Caches the flag object data (not the ORM object itself).
    Returns a dict or None.
    """
    cache_key = f"flag:config:{flag_name}"
    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    try:
        flag = FeatureFlag.objects.get(name=flag_name)
        flag_data = {
            "name": flag.name,
            "is_active": flag.is_active,
            "rollout_percentage": flag.rollout_percentage,
        }
        cache.set(cache_key, flag_data, FLAG_CACHE_TTL)
        return flag_data
    except FeatureFlag.DoesNotExist:
        # Cache the miss too — prevents DB hammering on bad flag names
        cache.set(cache_key, "NOT_FOUND", FLAG_CACHE_TTL)
        return None


def invalidate_flag_cache(flag_name: str):
    """
    Call this whenever a flag is updated (toggle, rollout change).
    Ensures stale cache doesn't serve wrong results after a change.
    """
    cache.delete(f"flag:config:{flag_name}")


def get_user_bucket(user_id: str, flag_name: str) -> int:
    """
    Deterministically assign user to bucket 0–99.
    SHA-256 of (user_id + flag_name) → first 8 hex chars → int → mod 100.
    """
    raw = f"{user_id}{flag_name}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:8], 16) % 100


def evaluate_flag(flag_name: str, user_id: str) -> dict:
    """
    Core evaluation engine with caching.
    Returns a consistent dict — never raises.
    """

    # ── Rule 1: Flag exists? ──────────────────────────────────────
    flag_data = _get_flag_cached(flag_name)
    if flag_data is None or flag_data == "NOT_FOUND":
        return {
            "enabled": False,
            "reason": "flag_not_found",
            "flag_name": flag_name,
            "user_id": user_id,
        }

    # ── Rule 2: Globally active? ──────────────────────────────────
    if not flag_data["is_active"]:
        return {
            "enabled": False,
            "reason": "flag_disabled",
            "flag_name": flag_name,
            "user_id": user_id,
        }

    # ── Rule 3: Full rollout shortcut ─────────────────────────────
    if flag_data["rollout_percentage"] >= 100:
        return {
            "enabled": True,
            "reason": "full_rollout",
            "flag_name": flag_name,
            "user_id": user_id,
        }

    # ── Rule 4: Zero rollout shortcut ─────────────────────────────
    if flag_data["rollout_percentage"] <= 0:
        return {
            "enabled": False,
            "reason": "zero_rollout",
            "flag_name": flag_name,
            "user_id": user_id,
        }

    # ── Rule 5: Hash-based rollout ────────────────────────────────
    bucket = get_user_bucket(user_id, flag_name)
    in_rollout = bucket < flag_data["rollout_percentage"]

    return {
        "enabled": in_rollout,
        "reason": "rollout" if in_rollout else "not_in_rollout",
        "flag_name": flag_name,
        "user_id": user_id,
        "bucket": bucket,
        "rollout_percentage": flag_data["rollout_percentage"],
    }