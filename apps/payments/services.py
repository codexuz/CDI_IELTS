# apps/payments/services.py
import hashlib
import hmac
from decimal import Decimal
from typing import Dict, Any

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.profiles.models import StudentProfile, StudentTopUpLog
from .models import Payment, PaymentStatus


def _click_sign(payload: Dict[str, Any]) -> str:
    secret = settings.CLICK["SECRET_KEY"].encode()
    base = (
        f"{payload.get('merchant_id','')}"
        f"{payload.get('amount','')}"
        f"{payload.get('transaction','')}"
        f"{payload.get('action','')}"
    ).encode()
    return hmac.new(secret, base, hashlib.md5).hexdigest()


def verify_click_request(payload: Dict[str, Any]) -> bool:
    provided = (payload.get("sign") or "").lower()
    expected = _click_sign(payload)
    return provided == expected


@transaction.atomic
def mark_payment_paid_and_topup(
    *, payment: Payment, webhook_payload: Dict[str, Any]
) -> Payment:

    if payment.status == PaymentStatus.PAID:
        return payment

    sp = payment.student
    StudentProfile.objects.filter(pk=sp.pk).update(
        balance=F("balance") + Decimal(payment.amount)
    )
    sp.refresh_from_db(fields=["balance"])
    StudentTopUpLog.objects.create(
        student=sp,
        amount=Decimal(payment.amount),
        new_balance=sp.balance,
        actor=None,
        note=f"Click top-up Payment<{payment.id}>",
    )

    payment.status = PaymentStatus.PAID
    payment.provider_payload = webhook_payload or {}
    payment.completed_at = timezone.now()
    payment.save(
        update_fields=["status", "provider_payload", "completed_at", "updated_at"]
    )
    return payment


def mark_payment_failed(
    *, payment: Payment, webhook_payload: Dict[str, Any]
) -> Payment:
    payment.status = PaymentStatus.FAILED
    payment.provider_payload = webhook_payload or {}
    payment.save(update_fields=["status", "provider_payload", "updated_at"])
    return payment
