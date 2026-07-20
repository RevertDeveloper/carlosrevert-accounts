from django.core.cache import cache


def is_rate_limited(request, scope: str, limit: int, window_seconds: int) -> bool:  # type: ignore[no-untyped-def]
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    address = (
        forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "unknown")
    )
    key = f"rate-limit:{scope}:{address}"
    if cache.add(key, 1, timeout=window_seconds):
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return False
    return count > limit
