# apps/users/admin.py
from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "fullname",
        "phone_number",
        "role",
        "telegram_id",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "is_active", "created_at")
    search_fields = ("fullname", "phone_number", "telegram_username", "telegram_id")
    readonly_fields = ("created_at", "updated_at", "last_activity")
