# FILE: feature_flags/views.py
# UPDATED FILE

from django.db.models import Count, Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .evaluator import evaluate_flag
from .assigner import assign_user
from .serializers import (
    EvaluateFlagSerializer,
    FeatureFlagSerializer,
    ExperimentSerializer,
    VariantSerializer,
    AssignUserSerializer,
    LogEventSerializer,
)
from .models import (
    FeatureFlag, Experiment, Variant,
    UserIdentifier, Assignment, MetricEvent,
)


# ── Health Check ──────────────────────────────────────────────────

@api_view(["GET"])
def health(request):
    return Response({
        "status": "ok",
        "service": "flagr",
        "version": "0.1.0",
    })


# ── Feature Flags (Phase 3, unchanged) ───────────────────────────

@api_view(["GET", "POST"])
def flag_list(request):
    if request.method == "GET":
        flags = FeatureFlag.objects.all()
        return Response(FeatureFlagSerializer(flags, many=True).data)

    serializer = FeatureFlagSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PATCH"])
def flag_detail(request, flag_name):
    try:
        flag = FeatureFlag.objects.get(name=flag_name)
    except FeatureFlag.DoesNotExist:
        return Response(
            {"error": f"Flag '{flag_name}' not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "GET":
        return Response(FeatureFlagSerializer(flag).data)

    serializer = FeatureFlagSerializer(flag, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def evaluate(request):
    serializer = EvaluateFlagSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    result = evaluate_flag(
        flag_name=serializer.validated_data["flag_name"],
        user_id=serializer.validated_data["user_id"],
    )
    return Response(result)


# ── Experiments (Phase 4, unchanged) ─────────────────────────────

@api_view(["GET", "POST"])
def experiment_list(request):
    if request.method == "GET":
        experiments = Experiment.objects.prefetch_related("variants").all()
        return Response(ExperimentSerializer(experiments, many=True).data)

    serializer = ExperimentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PATCH"])
def experiment_detail(request, experiment_id):
    try:
        experiment = Experiment.objects.prefetch_related("variants").get(
            id=experiment_id
        )
    except Experiment.DoesNotExist:
        return Response(
            {"error": f"Experiment '{experiment_id}' not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "GET":
        return Response(ExperimentSerializer(experiment).data)

    serializer = ExperimentSerializer(experiment, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def experiment_add_variant(request, experiment_id):
    try:
        experiment = Experiment.objects.get(id=experiment_id)
    except Experiment.DoesNotExist:
        return Response(
            {"error": f"Experiment '{experiment_id}' not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = VariantSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(experiment=experiment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def experiment_assign(request):
    serializer = AssignUserSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    result = assign_user(
        experiment_id=serializer.validated_data["experiment_id"],
        user_id=serializer.validated_data["user_id"],
    )

    if not result["success"]:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    return Response(result)


# ── Metrics (Phase 5, new) ────────────────────────────────────────

@api_view(["POST"])
def log_event(request):
    """
    POST /api/experiments/events/

    Log an impression or conversion for a user in an experiment.
    User must already be assigned to a variant — we look it up
    automatically so the caller doesn't need to pass variant_id.

    Duplicate events (same user + experiment + event_type) are
    silently ignored — idempotent by design.
    """
    serializer = LogEventSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    experiment_id = serializer.validated_data["experiment_id"]
    user_id = serializer.validated_data["user_id"]
    event_type = serializer.validated_data["event_type"]

    # Experiment must exist
    try:
        experiment = Experiment.objects.get(id=experiment_id)
    except Experiment.DoesNotExist:
        return Response(
            {"error": f"Experiment '{experiment_id}' not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # User must exist and be assigned
    try:
        user = UserIdentifier.objects.get(external_id=user_id)
        assignment = Assignment.objects.select_related("variant").get(
            user=user,
            experiment=experiment,
        )
    except UserIdentifier.DoesNotExist:
        return Response(
            {"error": f"User '{user_id}' has no assignment in this experiment."},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Assignment.DoesNotExist:
        return Response(
            {"error": f"User '{user_id}' has no assignment in this experiment."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # get_or_create = idempotent. Logging same event twice is a no-op.
    event, created = MetricEvent.objects.get_or_create(
        experiment=experiment,
        variant=assignment.variant,
        user=user,
        event_type=event_type,
    )

    return Response({
        "success": True,
        "created": created,          # False means it was a duplicate
        "user_id": user_id,
        "experiment_id": experiment_id,
        "variant_name": assignment.variant.name,
        "event_type": event_type,
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(["GET"])
def experiment_metrics(request, experiment_id):
    """
    GET /api/experiments/<id>/metrics/

    Returns aggregated impression + conversion counts per variant,
    plus conversion rate. Single query using annotation.
    """
    try:
        experiment = Experiment.objects.get(id=experiment_id)
    except Experiment.DoesNotExist:
        return Response(
            {"error": f"Experiment '{experiment_id}' not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    # One query: get all variants with annotated counts
    variants = Variant.objects.filter(experiment=experiment).annotate(
        impressions=Count(
            "events",
            filter=Q(events__event_type=MetricEvent.EventType.IMPRESSION)
        ),
        conversions=Count(
            "events",
            filter=Q(events__event_type=MetricEvent.EventType.CONVERSION)
        ),
    )

    results = []
    for variant in variants:
        impressions = variant.impressions
        conversions = variant.conversions
        conversion_rate = (
            round(conversions / impressions * 100, 2)
            if impressions > 0 else 0
        )
        results.append({
            "variant_id": variant.id,
            "variant_name": variant.name,
            "impressions": impressions,
            "conversions": conversions,
            "conversion_rate_pct": conversion_rate,
        })

    return Response({
        "experiment_id": experiment_id,
        "experiment_name": experiment.name,
        "status": experiment.status,
        "variants": results,
    })