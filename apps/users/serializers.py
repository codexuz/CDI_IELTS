# apps/users/serializers.py
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from django.db.models.functions import Lower
from rest_framework import serializers

from .models import User


# --------- Common (read) ----------
class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # parol / permission maydonlari chiqarilmaydi
        fields = (
            "id",
            "fullname",
            "phone_number",
            "role",
            "telegram_id",
            "telegram_username",
            "is_active",
            "is_staff",
            "last_activity",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


# --------- Me (partial update) ----------
class UserUpdateMeSerializer(serializers.ModelSerializer):
    telegram_username = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = User
        fields = ("fullname", "telegram_username")
        extra_kwargs = {
            "fullname": {"required": False},
        }

    def validate_telegram_username(self, v: Optional[str]) -> Optional[str]:
        if v in ("", None):
            return None
        v = v.strip().lstrip("@").lower()
        # Format tekshiruvi (manager bilan mos)
        if not re.compile(r"^[A-Za-z0-9_]{5,32}$").match(v):
            raise serializers.ValidationError(
                "Invalid Telegram username (5-32 chars, letters/digits/_)."
            )
        # Case-insensitive uniqueness (DB constraintdan oldin yumshoq xabar)
        user_id = self.instance.id if self.instance else None
        exists = (
            User.objects.filter(telegram_username__isnull=False)
            .annotate(_u=Lower("telegram_username"))
            .filter(_u=v)
            .exclude(id=user_id)
            .exists()
        )
        if exists:
            raise serializers.ValidationError(
                "This Telegram username is already taken."
            )
        return v

    def update(self, instance: User, validated_data: Dict[str, Any]) -> User:
        # only safe fields
        fullname = validated_data.get("fullname", None)
        if fullname is not None:
            instance.fullname = fullname.strip() or instance.fullname

        # normalize and set
        if "telegram_username" in validated_data:
            instance.telegram_username = validated_data["telegram_username"]

        instance.save(update_fields=["fullname", "telegram_username", "updated_at"])
        return instance


# --------- Admin update ----------
class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("fullname", "role", "is_active")
        extra_kwargs = {
            "fullname": {"required": False},
            "role": {"required": False},
            "is_active": {"required": False},
        }

    def validate_role(self, v: str) -> str:
        if v not in {User.Roles.SUPERADMIN, User.Roles.STUDENT, User.Roles.TEACHER}:
            raise serializers.ValidationError("Invalid role.")
        return v
