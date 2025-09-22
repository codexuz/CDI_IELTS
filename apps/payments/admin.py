# apps/payments/admin.py
from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "amount",
        "currency",
        "status",
        "provider",
        "created_at",
        "completed_at",
    )
    list_filter = ("status", "provider", "currency", "created_at")
    search_fields = (
        "id",
        "student__user__fullname",
        "provider_txn_id",
        "provider_invoice_id",
    )
    raw_id_fields = ("student",)
