# apps/accounts/serializers.py
from __future__ import annotations
from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

from django.db import transaction
from rest_framework import serializers

from apps.users.models import User
from .models import VerificationCode


# ============================
# Register flow
# ============================
class RegisterStartSerializer(serializers.Serializer):
    """
    Faqat foydalanuvchini yaratish.
    Telegram username bu bosqichda so'ralmaydi — u verify bosqichida bind qilinadi.
    """

    fullname = serializers.CharField(max_length=100)
    phone_number = serializers.CharField(max_length=20)
    role = serializers.ChoiceField(
        choices=[(User.Roles.STUDENT, "student"), (User.Roles.TEACHER, "teacher")]
    )

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        phone = attrs["phone_number"]
        if User.objects.filter(phone_number=phone).exists():
            raise serializers.ValidationError(
                {"phone_number": "This phone number is already registered."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> User:
        # telegram_username yuborilmaydi; binding verify paytida bo'ladi
        return User.objects.create_user(**validated_data)


class RegisterVerifySerializer(serializers.Serializer):
    """Verify faqat user_id + code qabul qiladi."""

    user_id = serializers.UUIDField()
    code = serializers.CharField(max_length=6)

    def _load_user(self, user_id: UUID) -> User:
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("User not found.") from exc

    def _load_vc_by_code(self, code: str) -> VerificationCode | None:
        # Eng so‘nggi, hali yaroqli (alive) va REGISTER purpose’dagi shu code
        return (
            VerificationCode.objects.alive()
            .filter(code=code, purpose=VerificationCode.Purpose.REGISTER)
            .order_by("-created_at")
            .first()
        )

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        user = self._load_user(attrs["user_id"])
        vc = self._load_vc_by_code(attrs["code"])
        if not vc or not vc.is_valid(attrs["code"]):
            raise serializers.ValidationError("Invalid or expired code.")

        # Xavfsizlik: shu VC’dagi telegram_id allaqachon boshqa userga bog‘langanmi?
        if (
            vc.telegram_id
            and User.objects.filter(telegram_id=vc.telegram_id)
            .exclude(id=user.id)
            .exists()
        ):
            raise serializers.ValidationError(
                "This Telegram is already bound to another user."
            )

        attrs["user"] = user
        attrs["vc"] = vc
        return attrs

    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> User:
        user: User = validated_data["user"]
        vc: VerificationCode = validated_data["vc"]

        # Binding — Telegram identifikatorlari VC’dan olinadi
        if vc.telegram_id:
            user.telegram_id = vc.telegram_id
        if vc.telegram_username and not user.telegram_username:
            user.telegram_username = (
                (vc.telegram_username or "").strip().lstrip("@").lower()
            )

        user.save(update_fields=["telegram_id", "telegram_username", "updated_at"])
        vc.consume()
        return user


# ============================
# Login flow (faqat telegram_id)
# ============================
class LoginVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)
    telegram_id = serializers.IntegerField()

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        t_id = attrs["telegram_id"]
        code = attrs["code"]

        vc = VerificationCode.objects.latest_alive_for(
            telegram_id=t_id,
            telegram_username=None,
            purpose=VerificationCode.Purpose.LOGIN,
        )
        if not vc or not vc.is_valid(code):
            raise serializers.ValidationError("Invalid or expired code.")

        user = User.objects.filter(telegram_id=t_id).first()
        if not user:
            raise serializers.ValidationError("User is not linked to this Telegram ID.")

        attrs["user"] = user
        attrs["vc"] = vc
        return attrs

    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> User:
        vc: VerificationCode = validated_data["vc"]
        vc.consume()
        return validated_data["user"]


# ============================
# OTP ingest (Bot → Backend)
# ============================
class OtpIngestSerializer(serializers.Serializer):
    """
    Bot OTP'ni backendga push qiladi.
    Agar shu tg_id (+purpose) uchun aktiv kod bo‘lsa — 409 (conflict) qaytaramiz.
    """

    telegram_id = serializers.IntegerField(required=False)
    telegram_username = serializers.CharField(required=False, allow_blank=True)
    code = serializers.CharField(max_length=6)
    purpose = serializers.ChoiceField(choices=VerificationCode.Purpose.choices)

    def validate_code(self, v: str) -> str:
        if len(v) != 6 or not v.isdigit():
            raise serializers.ValidationError("Code must be 6 digits.")
        return v

    @transaction.atomic
    def create(self, validated_data: Dict[str, Any]) -> VerificationCode:
        # username normalize
        tuser = validated_data.get("telegram_username") or None
        if tuser:
            tuser = tuser.strip().lstrip("@").lower()
            validated_data["telegram_username"] = tuser

        # aktiv bor-yo‘qligini tekshir
        exists = VerificationCode.objects.has_active(
            telegram_id=validated_data.get("telegram_id"),
            telegram_username=validated_data.get("telegram_username"),
            purpose=validated_data["purpose"],
        )
        if exists:
            # DRF view 409 qaytarishi uchun ValidationError tashlaymiz
            raise serializers.ValidationError(
                {"detail": "Active code exists", "expires_at": exists.expires_at},
                code="conflict",
            )

        return VerificationCode.objects.issue(**validated_data, ttl_minutes=2)


# ============================
# OTP status (Bot → Backend)
# ============================
class OtpStatusQuerySerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField(required=False)
    telegram_username = serializers.CharField(required=False, allow_blank=True)
    purpose = serializers.ChoiceField(choices=VerificationCode.Purpose.choices)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        if not attrs.get("telegram_id") and not attrs.get("telegram_username"):
            raise serializers.ValidationError(
                "telegram_id yoki telegram_username talab qilinadi."
            )
        # normalize username
        if attrs.get("telegram_username"):
            attrs["telegram_username"] = (
                attrs["telegram_username"].strip().lstrip("@").lower()
            )
        return attrs
