# FILE: feature_flags/views.py
# UPDATED FILE

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .evaluator import evaluate_flag
from .serializers import EvaluateFlagSerializer, FeatureFlagSerializer
from .models import FeatureFlag


# ── Health Check ─────────────────────────────────────────────────

@api_view(["GET"])
def health(request):
    """
    GET /api/health/
    Used by load balancers and monitoring tools.
    """
    return Response({
        "status": "ok",
        "service": "flagr",
        "version": "0.1.0",
    })


# ── Flag Evaluation ───────────────────────────────────────────────

@api_view(["POST"])
def evaluate(request):
    """
    POST /api/flags/evaluate/
    Body: { "flag_name": "dark-mode", "user_id": "user_001" }

    Returns whether the flag is enabled for this user and why.
    """
    serializer = EvaluateFlagSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    result = evaluate_flag(
        flag_name=serializer.validated_data["flag_name"],
        user_id=serializer.validated_data["user_id"],
    )
    return Response(result, status=status.HTTP_200_OK)


# ── Flag CRUD (create + list) ─────────────────────────────────────

@api_view(["GET", "POST"])
def flag_list(request):
    """
    GET  /api/flags/        → list all flags
    POST /api/flags/        → create a new flag
    """
    if request.method == "GET":
        flags = FeatureFlag.objects.all()
        serializer = FeatureFlagSerializer(flags, many=True)
        return Response(serializer.data)

    if request.method == "POST":
        serializer = FeatureFlagSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PATCH"])
def flag_detail(request, flag_name):
    """
    GET   /api/flags/<flag_name>/   → get one flag
    PATCH /api/flags/<flag_name>/   → update (toggle, change rollout %)
    """
    try:
        flag = FeatureFlag.objects.get(name=flag_name)
    except FeatureFlag.DoesNotExist:
        return Response(
            {"error": f"Flag '{flag_name}' not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "GET":
        serializer = FeatureFlagSerializer(flag)
        return Response(serializer.data)

    if request.method == "PATCH":
        serializer = FeatureFlagSerializer(flag, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)