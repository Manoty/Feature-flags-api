from django.urls import path, include

urlpatterns = [
    path("api/", include("feature_flags.urls")),
]