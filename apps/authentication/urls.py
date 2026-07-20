from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
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
