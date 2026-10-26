"""Small shared-cache rate limiter for public authentication forms."""

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 300
MAX_ATTEMPTS = 10


class RateLimitUnavailable(Exception):
    """Raised when the shared authentication throttle cannot be checked."""


def _cache_key(request, scope):
    remote_address = request.META.get(
        settings.AUTH_RATE_LIMIT_IP_HEADER, "unknown"
    ).split(",", 1)[0].strip()
    address_digest = hashlib.sha256(remote_address.encode("utf-8")).hexdigest()
    return f"auth-rate-limit:{scope}:{address_digest}"


def allow_attempt(request, scope):
    key = _cache_key(request, scope)
    try:
        if cache.add(key, 1, timeout=WINDOW_SECONDS):
            return True
        try:
            return cache.incr(key) <= MAX_ATTEMPTS
        except ValueError:
            return cache.add(key, 1, timeout=WINDOW_SECONDS)
    except Exception as exc:
        logger.exception("Could not update authentication rate limit")
        raise RateLimitUnavailable from exc


def clear_attempts(request, scope):
    key = _cache_key(request, scope)
    try:
        cache.delete(key)
    except Exception as exc:
        logger.exception("Could not clear authentication rate limit")
        raise RateLimitUnavailable from exc


