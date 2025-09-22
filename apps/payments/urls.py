# apps/payments/urls.py
from django.urls import path

from .views import create_topup, click_webhook, payment_status

urlpatterns = [
    path("topup/", create_topup, name="payments-topup"),
    path("status/", payment_status, name="payments-status"),
    path("click/webhook/", click_webhook, name="payments-click-webhook"),
]
