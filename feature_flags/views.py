from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(["GET"])
def health(request):
    return Response({
        "status": "ok",
        "service": "flagr",
        "version": "0.1.0",
    })