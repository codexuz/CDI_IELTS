# apps/profiles/serializers.py
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict

from rest_framework import serializers

from apps.users.models import User
from .models import StudentProfile, TeacherProfile, StudentApprovalLog, StudentTopUpLog


# -------- Common read --------
class StudentProfileReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ("id", "balance", "is_approved", "type", "created_at", "updated_at")
        read_only_fields = fields


class TeacherProfileReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherProfile
        fields = ("id", "created_at", "updated_at")
        read_only_fields = fields


# -------- Me --------
class ProfileMeSerializer(serializers.Serializer):
    user = serializers.SerializerMethodField()
    student_profile = StudentProfileReadSerializer(read_only=True)
    teacher_profile = TeacherProfileReadSerializer(read_only=True)

    def get_user(self, obj: User):
        return {
            "id": str(obj.id),
            "fullname": obj.fullname,
            "phone_number": obj.phone_number,
            "role": obj.role,
            "telegram_id": obj.telegram_id,
            "telegram_username": obj.telegram_username,
        }


# -------- Admin: Student actions --------
class StudentApproveSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ("is_approved",)

    def update(
        self, instance: StudentProfile, validated_data: Dict[str, Any]
    ) -> StudentProfile:
        instance.is_approved = validated_data["is_approved"]
        instance.save(update_fields=["is_approved", "type", "updated_at"])
        return instance


class StudentTopUpSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )

    def save(self, **kwargs) -> StudentProfile:
        instance: StudentProfile = self.context["instance"]
        amount = self.validated_data["amount"]
        instance.balance += amount
        instance.save(update_fields=["balance", "updated_at"])
        return instance


class StudentApprovalLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentApprovalLog
        fields = ["id", "approved", "note", "actor", "actor_name", "created_at"]

    def get_actor_name(self, obj):
        return getattr(obj.actor, "fullname", None)


class StudentTopUpLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentTopUpLog
        fields = [
            "id",
            "amount",
            "new_balance",
            "note",
            "actor",
            "actor_name",
            "created_at",
        ]

    def get_actor_name(self, obj):
        return getattr(obj.actor, "fullname", None)
