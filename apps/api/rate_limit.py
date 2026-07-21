from django.conf import settings
from django.core.cache import cache


def get_client_ip(request) -> str:  # type: ignore[no-untyped-def]
    remote = request.META.get("REMOTE_ADDR", "unknown")
    trusted_proxies = set(getattr(settings, "TRUSTED_PROXY_IPS", ()))
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if remote in trusted_proxies and forwarded:
        # Nginx Proxy Manager appends the real client as the last forwarded hop.
        return forwarded.split(",")[-1].strip() or remote
    return remote


def is_rate_limited(request, scope: str, limit: int, window_seconds: int) -> bool:  # type: ignore[no-untyped-def]
    address = get_client_ip(request)
    key = f"rate-limit:{scope}:{address}"
    if cache.add(key, 1, timeout=window_seconds):
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return False
    return count > limit
