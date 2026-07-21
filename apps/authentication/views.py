from urllib.parse import urlsplit

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

from .forms import (
    AccountPasswordChangeForm,
    AccountPasswordResetForm,
    AccountSetPasswordForm,
    LoginForm,
    RegistrationForm,
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
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="apps.authentication.backends.EmailOrUsernameModelBackend")
        return redirect(_safe_next_url(request))
    return render(
        request,
        "authentication/register.html",
        {"form": form, "next": _safe_next_url(request)},
    )


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
        {"form": form, "next": _safe_next_url(request)},
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
