"""API v2 URL configuration."""

from django.urls import include, path

from .router import router

urlpatterns = [
    path("", include(router.urls)),
]
