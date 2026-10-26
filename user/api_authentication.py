from rest_framework.authentication import BasicAuthentication, get_authorization_header
from rest_framework.exceptions import APIException, Throttled

from .rate_limit import (
    WINDOW_SECONDS,
    RateLimitUnavailable,
    allow_attempt,
    clear_attempts,
)


class RateLimitCacheUnavailable(APIException):
    status_code = 503
    default_detail = "Сервис авторизации временно недоступен. Попробуйте позже."
    default_code = "rate_limit_unavailable"


class RateLimitedBasicAuthentication(BasicAuthentication):
    """Apply the shared login rate limit to API Basic-auth attempts."""

    def authenticate(self, request):
        authorization = get_authorization_header(request).split()
        if not authorization or authorization[0].lower() != b"basic":
            return None

        try:
            allowed = allow_attempt(request, "login")
        except RateLimitUnavailable as exc:
            raise RateLimitCacheUnavailable() from exc
        if not allowed:
            raise Throttled(wait=WINDOW_SECONDS)

        result = super().authenticate(request)
        if result is not None:
            clear_attempts(request, "login")
        return result
