"""Configuración común compartida por todos los entornos de Django."""

from pathlib import Path

import environ

# Directorio raíz del proyecto y carga centralizada de las variables de entorno.
BASE_DIR = Path(__file__).resolve().parents[2]
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# Parámetros básicos de seguridad y hosts permitidos para la aplicación.
SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Aplicaciones de Django, dependencias de terceros y módulos propios del proyecto.
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "axes",
    "apps.users",
    "apps.plans",
    "apps.applications",
    "apps.usage",
    "apps.authentication",
    "apps.dashboard",
    "apps.api",
]

# Capas de middleware para seguridad, sesiones, CSRF, CORS y protección contra abusos.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

# Enrutamiento y motores de plantillas para las interfaces web síncrona y asíncrona.
ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Conexión a la base de datos; la URL se puede sustituir mediante el entorno.
DATABASES = {
    "default": env.db(
        "DATABASE_URL", default="postgres://accounts:accounts@localhost:10410/accounts"
    )
}

# Modelo de usuario, autenticación y rutas de navegación tras iniciar o cerrar sesión.
AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "apps.authentication.backends.EmailOrUsernameModelBackend",
]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "account"
LOGOUT_REDIRECT_URL = "login"

# Reglas mínimas aplicadas a las contraseñas de los usuarios.
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Configuración regional y gestión de fechas con zona horaria.
LANGUAGE_CODE = "es"
TIME_ZONE = env("TIME_ZONE", default="Europe/Madrid")
USE_I18N = True
USE_TZ = True

# Archivos estáticos servidos por WhiteNoise en despliegues de producción.
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {"staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Valores por defecto para autenticación, permisos, esquema y paginación de DRF.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework.authentication.SessionAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Carlos Revert Accounts API",
    "DESCRIPTION": "Identidad, planes y cuotas compartidas entre aplicaciones.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Orígenes autorizados para peticiones CORS y protección CSRF entre aplicaciones.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Configuración segura y duración de las cookies de sesión y CSRF.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_SAVE_EVERY_REQUEST = False

# Límites de intentos y tiempo de bloqueo de django-axes ante accesos fallidos.
AXES_FAILURE_LIMIT = env.int("AXES_FAILURE_LIMIT", default=5)
AXES_COOLOFF_TIME = int(env.int("AXES_COOLOFF_TIME_HOURS", default=1)) / 24
AXES_RESET_ON_SUCCESS = True

# Transporte de correo y parámetros de los códigos de verificación de email.
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@carlosrevert.es")
EMAIL_VERIFICATION_CODE_TTL_SECONDS = env.int("EMAIL_VERIFICATION_CODE_TTL_SECONDS", default=600)
EMAIL_VERIFICATION_MAX_ATTEMPTS = env.int("EMAIL_VERIFICATION_MAX_ATTEMPTS", default=5)
EMAIL_VERIFICATION_RESEND_INTERVAL_SECONDS = env.int(
    "EMAIL_VERIFICATION_RESEND_INTERVAL_SECONDS", default=60
)
EMAIL_VERIFICATION_RESEND_LIMIT = env.int("EMAIL_VERIFICATION_RESEND_LIMIT", default=5)

# Secretos de servicios internos y política de conservación y reembolso de cuotas.
INTERNAL_SERVICE_SECRET = env("INTERNAL_SERVICE_SECRET", default="")
QUOTA_REFUNDABLE_ERROR_CODES = env.list(
    "QUOTA_REFUNDABLE_ERROR_CODES", default=["before_processing"]
)
USAGE_EVENT_RETENTION_DAYS = env.int("USAGE_EVENT_RETENTION_DAYS", default=365)

# Registro centralizado en consola con nivel configurable por entorno.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
