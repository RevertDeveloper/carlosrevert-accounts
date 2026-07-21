from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.applications.models import ClientApplication
from apps.usage.models import UsageEvent
from apps.usage.services.quota_service import get_usage_summary


def health(request: HttpRequest) -> JsonResponse:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})


@login_required
def account(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "dashboard/account.html",
        {
            "summary": get_usage_summary(request.user),
            "events": UsageEvent.objects.filter(user=request.user).select_related("application")[
                :10
            ],
            "applications": ClientApplication.objects.filter(is_active=True),
        },
    )


@login_required
@require_POST
def delete_account(request: HttpRequest) -> HttpResponse:
    request.user.is_active = False
    request.user.save(update_fields=("is_active",))
    from django.contrib.auth import logout

    logout(request)
    return render(request, "dashboard/account_deleted.html")


def quota_exceeded(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/quota_exceeded.html")


def error_403(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    return render(request, "errors/403.html", status=403)


def error_404(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    return render(request, "errors/404.html", status=404)


def error_500(request: HttpRequest) -> HttpResponse:
    return render(request, "errors/500.html", status=500)
