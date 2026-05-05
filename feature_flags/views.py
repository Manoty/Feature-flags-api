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
)
from .models import FeatureFlag, Experiment, Variant


# ── Health Check ──────────────────────────────────────────────────

@api_view(["GET"])
def health(request):
    """GET /api/health/"""
    return Response({
        "status": "ok",
        "service": "flagr",
        "version": "0.1.0",
    })


# ── Feature Flags (Phase 3, unchanged) ───────────────────────────

@api_view(["GET", "POST"])
def flag_list(request):
    """
    GET  /api/flags/   → list all flags
    POST /api/flags/   → create a flag
    """
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
    """
    GET   /api/flags/<flag_name>/  → get one flag
    PATCH /api/flags/<flag_name>/  → update a flag
    """
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
    """POST /api/flags/evaluate/"""
    serializer = EvaluateFlagSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    result = evaluate_flag(
        flag_name=serializer.validated_data["flag_name"],
        user_id=serializer.validated_data["user_id"],
    )
    return Response(result)


# ── Experiments (Phase 4, new) ────────────────────────────────────

@api_view(["GET", "POST"])
def experiment_list(request):
    """
    GET  /api/experiments/   → list all experiments
    POST /api/experiments/   → create an experiment
    """
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
    """
    GET   /api/experiments/<id>/   → get one experiment
    PATCH /api/experiments/<id>/   → update status etc.
    """
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
    """
    POST /api/experiments/<id>/variants/
    Add a variant to an experiment.
    Body: { "name": "control", "weight": 50 }
    """
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
    """
    POST /api/experiments/assign/
    Assign a user to a variant in an experiment.
    Body: { "experiment_id": 1, "user_id": "user_001" }
    """
    serializer = AssignUserSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    result = assign_user(
        experiment_id=serializer.validated_data["experiment_id"],
        user_id=serializer.validated_data["user_id"],
    )

    if not result["success"]:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    return Response(result, status=status.HTTP_200_OK)