from django.urls import path
from . import views

urlpatterns = [
    # Health
    path("health/", views.health, name="health"),

    # Feature flags
    path("flags/", views.flag_list, name="flag-list"),
    path("flags/evaluate/", views.evaluate, name="flag-evaluate"),
    path("flags/<slug:flag_name>/", views.flag_detail, name="flag-detail"),
]