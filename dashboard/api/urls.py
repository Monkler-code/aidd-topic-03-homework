"""API root URL configuration."""

from django.urls import include, path

urlpatterns = [
    path("v1/", include("dashboard.api.v1.urls")),
    path("v2/", include("dashboard.api.v2.urls")),
]
