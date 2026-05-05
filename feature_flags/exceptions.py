# FILE: feature_flags/exceptions.py
# NEW FILE

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Wraps all DRF exceptions in a consistent envelope:

    {
        "error": true,
        "code": "not_found",
        "message": "Not found.",
        "detail": { ... }   ← original DRF error detail
    }

    This means clients always know exactly where to look
    for error info, regardless of which endpoint failed.
    """
    response = exception_handler(exc, context)

    if response is not None:
        original_data = response.data

        # Map HTTP status to a short code string
        code_map = {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
            429: "too_many_requests",
            500: "server_error",
        }

        response.data = {
            "error": True,
            "code": code_map.get(response.status_code, "error"),
            "message": _extract_message(original_data),
            "detail": original_data,
        }

    return response


def _extract_message(data) -> str:
    """Pull a human-readable string out of whatever DRF gives us."""
    if isinstance(data, dict):
        # Try common keys first
        for key in ("detail", "non_field_errors", "message"):
            if key in data:
                val = data[key]
                if isinstance(val, list):
                    return str(val[0])
                return str(val)
        # Fall back to first value
        first = next(iter(data.values()))
        if isinstance(first, list):
            return str(first[0])
        return str(first)
    if isinstance(data, list):
        return str(data[0])
    return str(data)