from django.urls import path

from . import views

urlpatterns = [
    path("", views.account, name="account"),
    path("account/delete/", views.delete_account, name="delete_account"),
    path("quota-exceeded/", views.quota_exceeded, name="quota_exceeded"),
]
