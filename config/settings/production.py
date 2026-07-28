from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

if not SECRET_KEY or len(SECRET_KEY) < 50 or SECRET_KEY.startswith("replace-with-"):  # noqa: F405
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be configured with a random value of at least 50 characters."
    )
SESSION_COOKIE_DOMAIN = env("SESSION_COOKIE_DOMAIN", default=".carlosrevert.es")  # noqa: F405
CSRF_COOKIE_DOMAIN = env("CSRF_COOKIE_DOMAIN", default=".carlosrevert.es")  # noqa: F405
TRUSTED_PROXY_IPS = env.list("TRUSTED_PROXY_IPS", default=["127.0.0.1"])  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "accounts_cache",
    }
}

# Never print password-reset links to production logs. SMTP credentials remain
# environment-only and must be configured before enabling password recovery.
EMAIL_BACKEND = env(  # noqa: F405
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
