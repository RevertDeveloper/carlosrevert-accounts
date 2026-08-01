from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf/", views.CsrfView.as_view(), name="api-csrf"),
    path("auth/me/", views.MeView.as_view(), name="api-me"),
    path("auth/register/", views.RegisterView.as_view(), name="api-register"),
    path("auth/verify-email/", views.VerifyEmailView.as_view(), name="api-verify-email"),
    path(
        "auth/verify-email/resend/",
        views.ResendEmailVerificationView.as_view(),
        name="api-resend-email-verification",
    ),
    path("auth/login/", views.LoginView.as_view(), name="api-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="api-logout"),
    path("usage/summary/", views.UsageSummaryView.as_view(), name="api-usage-summary"),
    path("usage/reserve/", views.ReserveUsageView.as_view(), name="api-usage-reserve"),
    path("usage/history/", views.UsageHistoryView.as_view(), name="api-usage-history"),
    path(
        "internal/usage/validate/",
        views.ValidateUsageView.as_view(),
        name="api-usage-validate",
    ),
    path(
        "usage/<uuid:request_id>/complete/",
        views.CompleteUsageView.as_view(),
        name="api-usage-complete",
    ),
    path("usage/<uuid:request_id>/fail/", views.FailUsageView.as_view(), name="api-usage-fail"),
    path("applications/", views.ApplicationsView.as_view(), name="api-applications"),
    path("admin/metrics/", views.MetricsView.as_view(), name="api-metrics"),
]
