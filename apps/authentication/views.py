from urllib.parse import urlsplit

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from apps.api.rate_limit import is_rate_limited, is_rate_limited_identifier
from apps.applications.models import ClientApplication
from apps.users.models import User

from .forms import (
    AccountPasswordChangeForm,
    AccountPasswordResetForm,
    AccountSetPasswordForm,
    LoginForm,
    RegistrationForm,
)
from .forms_verification import EmailResendForm, EmailVerificationForm
from .services import (
    EmailVerificationDeliveryError,
    send_email_verification_code,
    verify_email_code,
)


def _safe_next_url(request) -> str:  # type: ignore[no-untyped-def]
    candidate = request.POST.get("next") or request.GET.get("next") or ""
    if candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    parsed = urlsplit(candidate)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme == "https" and (
        hostname == "carlosrevert.es" or hostname.endswith(".carlosrevert.es")
    ):
        return candidate
    return "account"


def register(request):  # type: ignore[no-untyped-def]
    if request.user.is_authenticated:
        return redirect("account")
    form = RegistrationForm(request.POST or None)
    next_url = _safe_next_url(request)
    if request.method == "POST" and is_rate_limited(request, "web-register", 5, 3600):
        form.add_error(None, "Demasiados intentos de registro. Inténtalo más tarde.")
        return render(
            request,
            "authentication/register.html",
            {"form": form, "next": next_url},
            status=429,
        )
    if request.method == "POST" and form.is_valid():
        user = form.save()
        request.session["email_verification"] = {
            "user_id": user.pk,
            "email": user.email,
            "next": next_url,
        }
        try:
            send_email_verification_code(user)
        except EmailVerificationDeliveryError:
            messages.error(
                request,
                "No hemos podido enviar el código. Puedes solicitar otro desde esta pantalla.",
            )
        return redirect("email_verification")
    return render(
        request,
        "authentication/register.html",
        {"form": form, "next": next_url},
    )


def email_verification(request):  # type: ignore[no-untyped-def]
    pending = request.session.get("email_verification", {})
    initial_email = pending.get("email", "")
    next_url = pending.get("next") or _safe_next_url(request)
    form = EmailVerificationForm(
        request.POST or None,
        initial={"email": initial_email} if request.method == "GET" else None,
    )
    if request.method == "POST":
        if is_rate_limited(request, "web-email-verify", 10, 600):
            form.add_error(None, "Demasiados intentos. Inténtalo más tarde.")
        elif form.is_valid():
            user = verify_email_code(form.cleaned_data["email"], form.cleaned_data["code"])
            if user is not None:
                request.session.pop("email_verification", None)
                login(
                    request,
                    user,
                    backend="apps.authentication.backends.EmailOrUsernameModelBackend",
                )
                return redirect(next_url)
            form.add_error("code", "El código no es válido o ha caducado.")
    return render(
        request,
        "authentication/email_verification.html",
        {"form": form, "next": next_url},
    )


@require_POST
def resend_email_verification(request):  # type: ignore[no-untyped-def]
    form = EmailResendForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data["email"]
        limited = (
            is_rate_limited(
                request,
                "web-email-verification-resend-ip",
                settings.EMAIL_VERIFICATION_RESEND_LIMIT,
                3600,
            )
            or is_rate_limited_identifier(
                "web-email-verification-resend-email",
                email,
                settings.EMAIL_VERIFICATION_RESEND_LIMIT,
                3600,
            )
            or is_rate_limited_identifier(
                "web-email-verification-resend-cooldown",
                email,
                1,
                settings.EMAIL_VERIFICATION_RESEND_INTERVAL_SECONDS,
            )
        )
        if limited:
            messages.error(request, "Demasiados reenvíos. Inténtalo más tarde.")
        else:
            user = User.objects.filter(
                email__iexact=email, is_active=True, is_blocked=False, email_verified=False
            ).first()
            if user is not None:
                try:
                    send_email_verification_code(user)
                except EmailVerificationDeliveryError:
                    messages.error(
                        request, "No hemos podido enviar el código. Inténtalo más tarde."
                    )
            messages.success(
                request,
                "Si existe una cuenta pendiente con ese correo, recibirás un nuevo código.",
            )
    else:
        messages.error(request, "Introduce un correo electrónico válido.")
    return redirect("email_verification")


def login_view(request):  # type: ignore[no-untyped-def]
    if request.user.is_authenticated:
        return redirect("account")
    form = LoginForm(request, request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(_safe_next_url(request))
    return render(
        request,
        "authentication/login.html",
        {
            "form": form,
            "next": _safe_next_url(request),
            "applications": ClientApplication.objects.filter(is_active=True).ordered_for_launcher(),
        },
    )


@require_POST
@login_required
def logout_view(request):  # type: ignore[no-untyped-def]
    logout(request)
    return render(request, "authentication/logout.html")


class AccountPasswordResetView(SuccessMessageMixin, PasswordResetView):
    form_class = AccountPasswordResetForm
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.txt"
    success_url = reverse_lazy("password_reset_done")
    success_message = (
        "Si existe una cuenta con ese correo, recibirás instrucciones para "
        "restablecer la contraseña."
    )


class AccountPasswordResetDoneView(PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"


class AccountPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = AccountSetPasswordForm
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("login")


class AccountPasswordChangeView(PasswordChangeView):
    form_class = AccountPasswordChangeForm
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("account")
