# apps/accounts/views.py
from django.conf import settings
from rest_framework import generics, status, throttling, permissions
from rest_framework.response import Response

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
)

from .serializers import (
    RegisterStartSerializer,
    RegisterVerifySerializer,
    LoginVerifySerializer,
    OtpIngestSerializer,
)
from .services import issue_tokens


# ============================
# Throttles (DoS/Bruteforce)
# ============================
class OTPIngestThrottle(throttling.UserRateThrottle):
    scope = (
        "otp_ingest"  # settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["otp_ingest"]
    )


class OTPVerifyThrottle(throttling.UserRateThrottle):
    scope = "otp_verify"


# ============================
# Views
# ============================


@extend_schema(
    tags=["accounts"],
    summary="Register start",
    description=(
        "Foydalanuvchini yaratadi (users). Role bo‘yicha profil signal orqali **auto** yaratiladi:\n"
        "- student → StudentProfile(balance=0, is_approved=False → type=online)\n"
        "- teacher → TeacherProfile\n\n"
        "Keyingi bosqich: Telegram botdan 6 xonali kod olib `/api/accounts/register/verify/` da tekshirish."
    ),
    request=RegisterStartSerializer,
    responses={
        201: OpenApiResponse(
            response=dict,
            description='{"message": "...", "user_id": "<uuid>"}',
        ),
        400: OpenApiResponse(description="Validation error"),
    },
)
class RegisterStartView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterStartSerializer
    throttle_classes = [OTPVerifyThrottle]

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response(
            {
                "message": "User created. Verify with Telegram code.",
                "user_id": str(user.id),
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["accounts"],
    summary="Register verify (Telegram OTP)",
    description=(
        "Bot yuborgan **register** purpose’dagi kodni tekshiradi.\n"
        "Muvaffaqiyatli bo‘lsa, `user.telegram_id` ni **bind** qiladi va JWT qaytaradi."
    ),
    request=RegisterVerifySerializer,
    responses={
        200: OpenApiResponse(
            response=dict,
            description='{"message":"Registration completed.","access":"...","refresh":"..."}',
        ),
        400: OpenApiResponse(description="Invalid/expired code yoki binding xatosi"),
    },
)
class RegisterVerifyView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterVerifySerializer
    throttle_classes = [OTPVerifyThrottle]

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        tokens = issue_tokens(user)
        return Response(
            {"message": "Registration completed.", **tokens},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["accounts"],
    summary="Login verify (Telegram OTP)",
    description=(
        "Faqat Telegram OTP orqali login.\n"
        "Body’da `code` va **`telegram_id` yoki `telegram_username`** bo‘lishi shart."
    ),
    request=LoginVerifySerializer,
    responses={
        200: OpenApiResponse(
            response=dict,
            description='{"message":"Login success.","access":"...","refresh":"..."}',
        ),
        400: OpenApiResponse(description="Invalid/expired code yoki user topilmadi"),
    },
)
class LoginVerifyView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginVerifySerializer
    throttle_classes = [OTPVerifyThrottle]

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        tokens = issue_tokens(user)
        return Response(
            {"message": "Login success.", **tokens},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["accounts"],
    summary="OTP ingest (Bot → Backend)",
    description=(
        "Telegram bot shu endpointga kodni push qiladi. 2 daqiqa amal qiladi (bot siyosati).\n"
        "**Xavfsizlik**: `X-Bot-Token` header’da shared-secret bo‘lishi shart."
    ),
    request=OtpIngestSerializer,
    parameters=[
        OpenApiParameter(
            name="X-Bot-Token",
            type=str,
            location=OpenApiParameter.HEADER,
            required=True,
            description="Shared secret (settings.TELEGRAM_BOT_INGEST_TOKEN)",
        )
    ],
    responses={
        201: OpenApiResponse(
            response=dict,
            description='{"status":"stored","expires_at":"2025-09-12T15:44:00Z"}',
        ),
        401: OpenApiResponse(description="Unauthorized (X-Bot-Token mos emas)"),
        400: OpenApiResponse(description="Validation error"),
    },
)
class OtpIngestView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = OtpIngestSerializer
    throttle_classes = [OTPIngestThrottle]

    def create(self, request, *args, **kwargs):
        expected = getattr(settings, "TELEGRAM_BOT_INGEST_TOKEN", None)
        provided = request.headers.get("X-Bot-Token")
        if expected and provided != expected:
            return Response(
                {"detail": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
            )

        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vc = ser.save()
        return Response(
            {"status": "stored", "expires_at": vc.expires_at},
            status=status.HTTP_201_CREATED,
        )
