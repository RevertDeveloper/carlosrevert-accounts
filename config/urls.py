"""Enrutador raíz: reúne la interfaz web, la API y la documentación del servicio."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.dashboard import views as dashboard_views

handler403 = "apps.dashboard.views.error_403"
handler404 = "apps.dashboard.views.error_404"
handler500 = "apps.dashboard.views.error_500"

# Las rutas de la API permanecen versionadas para permitir evolución compatible
# con las aplicaciones cliente ya desplegadas.
urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", dashboard_views.health, name="health"),
    path("api/v1/", include("apps.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("", include("apps.authentication.urls")),
    path("", include("apps.dashboard.urls")),
    path("terms/", TemplateView.as_view(template_name="legal/terms.html"), name="terms"),
    path("privacy/", TemplateView.as_view(template_name="legal/privacy.html"), name="privacy"),
]

if settings.DEBUG:
    # Django solo sirve estáticos directamente durante desarrollo local.
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
