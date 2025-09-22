# apps/payments/serializers.py

from django.conf import settings
from rest_framework import serializers

from .models import Payment


class PaymentCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_amount(self, v):
        min_amt = settings.PAYMENTS["MIN_TOPUP"]
        max_amt = settings.PAYMENTS["MAX_TOPUP"]
        if v < min_amt:
            raise serializers.ValidationError(f"Minimal summa {min_amt} UZS.")
        if v > max_amt:
            raise serializers.ValidationError(f"Maksimal summa {max_amt} UZS.")
        return v


class PaymentPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "status", "amount", "currency", "created_at", "completed_at"]


class PaymentDetailSerializer(serializers.ModelSerializer):
    student = serializers.UUIDField(source="student.id", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "student",
            "provider",
            "status",
            "amount",
            "currency",
            "provider_invoice_id",
            "provider_txn_id",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields
