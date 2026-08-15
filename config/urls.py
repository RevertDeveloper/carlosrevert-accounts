"""Enrutador raíz: reúne la interfaz web, la API y la documentación del servicio."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.dashboard import views as dashboard_views


def robots_txt(_request):  # type: ignore[no-untyped-def]
    content = "\n\n".join(
        f"User-agent: {user_agent}\nAllow: /terms/\nAllow: /privacy/\nAllow: /llms.txt\n"
        "Disallow: /admin/\nDisallow: /api/\nDisallow: /account/\n"
        "Disallow: /login/\nDisallow: /register/\nDisallow: /password/"
        for user_agent in ("OAI-SearchBot", "GPTBot", "Googlebot", "*")
    ) + "\n\nSitemap: https://cuenta.carlosrevert.es/sitemap.xml\n"
    return HttpResponse(content, content_type="text/plain; charset=utf-8")


def sitemap_xml(_request):  # type: ignore[no-untyped-def]
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://cuenta.carlosrevert.es/terms/</loc></url>
  <url><loc>https://cuenta.carlosrevert.es/privacy/</loc></url>
</urlset>
"""
    return HttpResponse(content, content_type="application/xml; charset=utf-8")


def llms_txt(_request):  # type: ignore[no-untyped-def]
    content = """# Carlos Revert Cuenta

Carlos Revert Cuenta es el servicio de identidad común para las aplicaciones públicas de Carlos Revert. Gestiona registro, inicio de sesión, verificación de correo, planes de uso y cuotas compartidas.

## Acceso público

- [Términos](https://cuenta.carlosrevert.es/terms/)
- [Privacidad](https://cuenta.carlosrevert.es/privacy/)
- [Carlos Revert](https://carlosrevert.es/)

Las cuentas, credenciales, sesiones, datos de usuario y operaciones de administración son privados.
"""
    return HttpResponse(content, content_type="text/plain; charset=utf-8")

handler403 = "apps.dashboard.views.error_403"
handler404 = "apps.dashboard.views.error_404"
handler500 = "apps.dashboard.views.error_500"

# Las rutas de la API permanecen versionadas para permitir evolución compatible
# con las aplicaciones cliente ya desplegadas.
urlpatterns = [
    path("robots.txt", robots_txt, name="robots-txt"),
    path("sitemap.xml", sitemap_xml, name="sitemap-xml"),
    path("llms.txt", llms_txt, name="llms-txt"),
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
