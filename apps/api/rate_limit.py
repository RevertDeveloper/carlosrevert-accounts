"""Utilidades de limitación de peticiones basadas en caché y claves no reversibles."""

import hashlib

from django.conf import settings
from django.core.cache import cache


def get_client_ip(request) -> str:  # type: ignore[no-untyped-def]
    """Obtiene la IP cliente y solo confía en X-Forwarded-For desde proxies declarados."""
    remote = request.META.get("REMOTE_ADDR", "unknown")
    trusted_proxies = set(getattr(settings, "TRUSTED_PROXY_IPS", ()))
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if remote in trusted_proxies and forwarded:
        # Nginx Proxy Manager añade el cliente real como último salto reenviado.
        return forwarded.split(",")[-1].strip() or remote
    return remote


def is_rate_limited(request, scope: str, limit: int, window_seconds: int) -> bool:  # type: ignore[no-untyped-def]
    """Aplica un límite por IP al ámbito indicado y a su ventana temporal."""
    return is_rate_limited_identifier(
        scope,
        get_client_ip(request),
        limit,
        window_seconds,
    )


def is_rate_limited_identifier(
    scope: str, identifier: str, limit: int, window_seconds: int
) -> bool:
    """Limita un identificador no basado en IP sin guardarlo en la clave de caché."""
    digest = hashlib.sha256(identifier.strip().lower().encode("utf-8")).hexdigest()
    key = f"rate-limit:{scope}:{digest}"
    if cache.add(key, 1, timeout=window_seconds):
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return False
    return count > limit
