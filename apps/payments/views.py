# apps/payments/views.py
from __future__ import annotations

import logging
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.profiles.models import StudentProfile
from .models import Payment, PaymentStatus, PaymentProvider
from .serializers import (
    PaymentCreateSerializer,
    PaymentPublicSerializer,
    PaymentDetailSerializer,
)
from .services import (
    verify_click_request,
    mark_payment_paid_and_topup,
    mark_payment_failed,
)

log = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Top-up session create (redirect to Click)
# ------------------------------------------------------------------------------
@extend_schema(
    tags=["Payments"],
    summary="Top-up sessiya yaratish (Click redirect URL qaytaradi)",
    description=(
        "Foydalanuvchi balansini to‘ldirish uchun topshiriq yaratadi. "
        "Natijada `redirect_url` qaytadi — front shu URLga redirect qilib, "
        "to‘lovni Click sahifasida tugatadi."
    ),
    request=PaymentCreateSerializer,
    responses={201: PaymentPublicSerializer},
)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_topup(request):
    ser = PaymentCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    # Student borligini tekshirish
    sp = get_object_or_404(StudentProfile, user=request.user)

    payment = Payment.objects.create(
        student=sp,
        provider=PaymentProvider.CLICK,
        status=PaymentStatus.CREATED,
        amount=ser.validated_data["amount"],
        currency="UZS",
    )

    # Click redirect URL (sizning integratsiya formatlaringizga moslang)
    redirect_url = (
        f"{settings.CLICK['BASE_URL']}"
        f"?merchant_id={settings.CLICK['MERCHANT_ID']}"
        f"&amount={payment.amount}"
        f"&transaction={payment.id}"
        f"&return_url={settings.CLICK['RETURN_URL']}?payment_id={payment.id}"
        f"&cancel_url={settings.CLICK['CANCEL_URL']}?payment_id={payment.id}"
    )

    data = PaymentPublicSerializer(payment).data
    data["redirect_url"] = redirect_url
    return Response(data, status=status.HTTP_201_CREATED)


# ------------------------------------------------------------------------------
# Click webhook (prepare/check/complete/cancel)
#  - IP allowlist
#  - Signature verification
#  - Idempotent & safe updates
# ------------------------------------------------------------------------------
@extend_schema(
    tags=["Payments"],
    summary="Click webhook (prepare/check/complete/cancel)",
    description=(
        "Click tomonidan yuboriladigan webhook. Signature va IP tekshiriladi. "
        "`prepare/check` → payment PENDING; "
        "`complete/pay` → PAID (balansga top-up yoziladi) yoki FAILED; "
        "`cancel` → CANCELED."
    ),
    request=OpenApiTypes.OBJECT,
    responses={200: OpenApiTypes.OBJECT},
)
@csrf_exempt
@api_view(["POST"])
def click_webhook(request):
    # 1) IP allowlist
    allowed_ips = set(settings.CLICK.get("ALLOWED_IPS", []))
    remote_ip = request.META.get("REMOTE_ADDR")
    if allowed_ips and remote_ip not in allowed_ips:
        log.warning("Click webhook blocked by IP: %s", remote_ip)
        return Response({"error": "IP not allowed"}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data.copy()

    # 2) Signature verification
    if not verify_click_request(payload):
        log.warning("Click webhook invalid signature: %s", payload)
        return Response(
            {"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST
        )

    # 3) Payment topish (transaction lock bilan)
    txn = payload.get("transaction") or payload.get("merchant_trans_id") or ""
    try:
        payment_id = UUID(str(txn))
    except Exception:  # noto‘g‘ri UUID bo‘lishi mumkin
        return Response(
            {"error": "Invalid transaction id"}, status=status.HTTP_400_BAD_REQUEST
        )

    action = str(payload.get("action", "")).lower()
    error = str(payload.get("error", "0"))  # Click odatda '0' bo‘lsa OK
    error_note = payload.get("error_note", "")

    with transaction.atomic():
        try:
            payment = Payment.objects.select_for_update().get(id=payment_id)
        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # prepare / check
        if action in {"prepare", "check"}:
            if payment.status in {
                PaymentStatus.CREATED,
                PaymentStatus.FAILED,
                PaymentStatus.CANCELED,
            }:
                payment.status = PaymentStatus.PENDING
                payment.provider_invoice_id = payload.get("invoice_id", "")
                payment.provider_txn_id = payload.get("click_trans_id", "")
                payment.provider_payload = payload
                payment.error_code = error
                payment.error_note = error_note
                payment.save(
                    update_fields=[
                        "status",
                        "provider_invoice_id",
                        "provider_txn_id",
                        "provider_payload",
                        "error_code",
                        "error_note",
                        "updated_at",
                    ]
                )
            return Response({"status": "pending", "payment_id": str(payment.id)})

        # complete / pay
        if action in {"complete", "pay"}:
            # Click error != 0 → failure
            if error != "0":
                payment.error_code = error
                payment.error_note = error_note or "Provider declined"
                mark_payment_failed(payment=payment, webhook_payload=payload)
                return Response({"status": "failed", "payment_id": str(payment.id)})

            try:
                mark_payment_paid_and_topup(payment=payment, webhook_payload=payload)
            except Exception as exc:
                log.exception("Top-up failed for payment %s: %s", payment.id, exc)
                mark_payment_failed(payment=payment, webhook_payload=payload)
                return Response(
                    {"error": "Top-up failed"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response({"status": "paid", "payment_id": str(payment.id)})

        # cancel
        if action == "cancel":
            payment.status = PaymentStatus.CANCELED
            payment.provider_payload = payload
            payment.error_code = error
            payment.error_note = error_note or "Canceled by user/provider"
            payment.save(
                update_fields=[
                    "status",
                    "provider_payload",
                    "error_code",
                    "error_note",
                    "updated_at",
                ]
            )
            return Response({"status": "canceled", "payment_id": str(payment.id)})

        # unknown action
        return Response({"error": "Unknown action"}, status=status.HTTP_400_BAD_REQUEST)


# ------------------------------------------------------------------------------
# Payment status (frontend polling)
# ------------------------------------------------------------------------------
@extend_schema(
    tags=["Payments"],
    summary="Payment status (frontend polling uchun)",
    description=(
        "Frontend to‘lovdan qaytgach, `payment_id` bo‘yicha statusni tekshiradi. "
        "`paid` bo‘lsa — balans allaqachon to‘ldirilgan bo‘ladi."
    ),
    parameters=[
        OpenApiParameter(
            "payment_id",
            OpenApiTypes.UUID,
            OpenApiParameter.QUERY,
            description="Payment ID (uuid)",
        ),
    ],
    responses={200: PaymentDetailSerializer},
)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def payment_status(request):
    pid = request.query_params.get("payment_id")
    payment = get_object_or_404(Payment, id=pid, student__user=request.user)
    return Response(PaymentDetailSerializer(payment).data)
