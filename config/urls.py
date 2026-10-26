from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

from user.rate_limit import RateLimitUnavailable, allow_attempt, clear_attempts


def admin_login(request):
    if request.method != "POST":
        return admin.site.login(request)

    try:
        if not allow_attempt(request, "login"):
            return HttpResponse(
                "Слишком много попыток. Попробуйте позже.",
                status=429,
                headers={"Retry-After": "300"},
            )
    except RateLimitUnavailable:
        return HttpResponse(
            "Сервис авторизации временно недоступен. Попробуйте позже.",
            status=503,
            headers={"Retry-After": "60"},
        )

    response = admin.site.login(request)
    if response.status_code == 302 and request.user.is_authenticated:
        try:
            clear_attempts(request, "login")
        except RateLimitUnavailable:
            return HttpResponse(
                "Сервис авторизации временно недоступен. Попробуйте позже.",
                status=503,
                headers={"Retry-After": "60"},
            )
    return response


urlpatterns = [
    path("admin/login/", admin_login, name="admin_login"),
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("user/", include("user.urls")),
]
