from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", views.account, name="account"),
    path(
        "account/",
        RedirectView.as_view(pattern_name="account", permanent=False),
        name="legacy_account",
    ),
    path("account/delete/", views.delete_account, name="delete_account"),
    path("quota-exceeded/", views.quota_exceeded, name="quota_exceeded"),
]
