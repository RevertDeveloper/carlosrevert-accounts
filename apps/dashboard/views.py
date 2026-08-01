from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.applications.models import ClientApplication
from apps.authentication.forms import AccountUpdateForm
from apps.authentication.services import (
    EmailVerificationDeliveryError,
    send_email_verification_code,
)
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
    original_email = request.user.email.lower()
    account_form = AccountUpdateForm(request.POST or None, instance=request.user)
    if request.method == "POST" and account_form.is_valid():
        updated_user = account_form.save(commit=False)
        email_changed = updated_user.email.lower() != original_email
        if email_changed:
            updated_user.email_verified = False
            updated_user.save()
            request.session["email_verification"] = {
                "user_id": updated_user.pk,
                "email": updated_user.email,
                "next": "account",
            }
            logout(request)
            try:
                send_email_verification_code(updated_user)
            except EmailVerificationDeliveryError:
                messages.error(
                    request,
                    "El correo cambió, pero no hemos podido enviar el código de verificación.",
                )
            else:
                messages.info(
                    request,
                    "Hemos enviado un código a tu nuevo correo. Verifícalo para continuar.",
                )
            return redirect("email_verification")
        updated_user.save()
        messages.success(request, "Los datos de tu cuenta se han actualizado.")
        return redirect("account")
    return render(
        request,
        "dashboard/account.html",
        {
            "summary": get_usage_summary(request.user),
            "events": UsageEvent.objects.filter(user=request.user).select_related("application")[
                :10
            ],
            "applications": ClientApplication.objects.filter(is_active=True),
            "account_form": account_form,
        },
    )


@login_required
@require_POST
def delete_account(request: HttpRequest) -> HttpResponse:
    request.user.is_active = False
    request.user.save(update_fields=("is_active",))
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
