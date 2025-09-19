#  apps/users/views.py
from __future__ import annotations

from datetime import datetime

from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import (
    UserReadSerializer,
    UserUpdateMeSerializer,
    AdminUserUpdateSerializer,
)


# ---------- Health ----------
@extend_schema(
    tags=["users"], responses={200: OpenApiResponse(description='{"status":"ok"}')}
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def ping(_request):
    return Response({"status": "ok", "app": "users"}, status=status.HTTP_200_OK)


# ---------- /users/me ----------
class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["users"], summary="Get current user", responses=UserReadSerializer
    )
    def get(self, request):
        # eng tez: bevosita request.user dan serialize
        serializer = UserReadSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["users"],
        summary="Update current user (partial)",
        request=UserUpdateMeSerializer,
        responses={
            200: UserReadSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def patch(self, request):
        serializer = UserUpdateMeSerializer(
            instance=request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserReadSerializer(user).data, status=status.HTTP_200_OK)


# ---------- Admin: users CRUD (read/list + partial update) ----------
class IsAdmin(permissions.IsAdminUser):
    # future: superadmin-only bo‘lsa bu yerda toraytirish mumkin
    pass


@extend_schema(tags=["users"])
class UserAdminViewSet(viewsets.ModelViewSet):
    """
    Admin-only ro'yxat, ko'rish, qisman yangilash.
    Parol, permissions bilan ishlamaymiz (alohida admin panel uchun).
    """

    permission_classes = [IsAdmin]
    http_method_names = ["get", "patch", "head", "options"]
    queryset = (
        User.objects.all()
        .only(
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
        .order_by("-created_at")
    )

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return UserReadSerializer
        return AdminUserUpdateSerializer

    # ---- Filtering (q, role, has_telegram, created_from, created_to) ----
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="q",
                description="Search in fullname/phone/username",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="role",
                description="student|teacher|superadmin",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="has_telegram", description="true|false", required=False, type=bool
            ),
            OpenApiParameter(
                name="created_from",
                description="ISO date, e.g. 2025-09-01",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="created_to",
                description="ISO date, e.g. 2025-09-17",
                required=False,
                type=str,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        q = request.query_params.get("q")
        role = request.query_params.get("role")
        has_telegram = request.query_params.get("has_telegram")
        created_from = request.query_params.get("created_from")
        created_to = request.query_params.get("created_to")

        if q:
            q_norm = q.strip().lower()
            qs = qs.filter(
                Q(fullname__icontains=q_norm)
                | Q(phone_number__icontains=q_norm)
                | Q(telegram_username__icontains=q_norm)
            )

        if role in {User.Roles.STUDENT, User.Roles.TEACHER, User.Roles.SUPERADMIN}:
            qs = qs.filter(role=role)

        if has_telegram in {"true", "false"}:
            if has_telegram == "true":
                qs = qs.filter(
                    Q(telegram_id__isnull=False) | Q(telegram_username__isnull=False)
                )
            else:
                qs = qs.filter(
                    Q(telegram_id__isnull=True) & Q(telegram_username__isnull=True)
                )

        # date filters (UTC, inclusive)
        try:
            if created_from:
                dt_from = datetime.fromisoformat(created_from)
                qs = qs.filter(created_at__gte=dt_from)
            if created_to:
                dt_to = datetime.fromisoformat(created_to)
                qs = qs.filter(created_at__lte=dt_to)
        except ValueError:
            # noto‘g‘ri sana formatida bo‘lsa filtrni e’tiborsiz qoldiramiz
            pass

        page = self.paginate_queryset(qs)
        if page is not None:
            ser = UserReadSerializer(page, many=True)
            return self.get_paginated_response(ser.data)
        ser = UserReadSerializer(qs, many=True)
        return Response(ser.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Admin: partial update user",
        request=AdminUserUpdateSerializer,
        responses=UserReadSerializer,
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        ser = AdminUserUpdateSerializer(instance, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response(UserReadSerializer(user).data, status=status.HTTP_200_OK)
