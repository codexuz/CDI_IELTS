from django.contrib import admin
from .models import VerificationCode


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_id",
        "telegram_username",
        "purpose",
        "code",
        "consumed",
        "created_at",
        "expires_at",
    )
    list_filter = ("purpose", "consumed", "created_at")
    search_fields = ("telegram_username", "telegram_id", "code")
    readonly_fields = ("created_at", "expires_at")
