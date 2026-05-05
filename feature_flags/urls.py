from django.urls import path
from . import views

urlpatterns = [

    # ── Health ────────────────────────────────────────────────────
    path("health/", views.health, name="health"),

    # ── Feature Flags (Phase 3) ───────────────────────────────────
    path("flags/", views.flag_list, name="flag-list"),
    path("flags/evaluate/", views.evaluate, name="flag-evaluate"),
    path("flags/<slug:flag_name>/", views.flag_detail, name="flag-detail"),

    # ── Experiments (Phase 4) ─────────────────────────────────────
    path("experiments/", views.experiment_list, name="experiment-list"),
    path("experiments/assign/", views.experiment_assign, name="experiment-assign"),
    path("experiments/<int:experiment_id>/", views.experiment_detail, name="experiment-detail"),
    path("experiments/<int:experiment_id>/variants/", views.experiment_add_variant, name="experiment-add-variant"),

]