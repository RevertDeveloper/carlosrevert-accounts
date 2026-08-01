from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("email-verification/", views.email_verification, name="email_verification"),
    path(
        "email-verification/resend/",
        views.resend_email_verification,
        name="email_verification_resend",
    ),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password-reset/", views.AccountPasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        views.AccountPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        views.AccountPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("password-change/", views.AccountPasswordChangeView.as_view(), name="password_change"),
]
