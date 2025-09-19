# apps/profiles/views.py
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response

from .models import (
    StudentProfile,
    TeacherProfile,
    StudentApprovalLog,
    StudentTopUpLog,
)
from .serializers import (
    ProfileMeSerializer,
    StudentProfileReadSerializer,
    TeacherProfileReadSerializer,
    StudentApproveSerializer,
    StudentTopUpSerializer,
    StudentApprovalLogSerializer,
    StudentTopUpLogSerializer,
)
from .permissions import IsTeacherOrSuperAdmin


# ---------- /profiles/me ----------
@extend_schema(
    tags=["profiles"], summary="Get current user profile", responses=ProfileMeSerializer
)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    u = request.user
    serializer = ProfileMeSerializer(u)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ---------- Admin-ish: Student profiles (teacher yoki superadmin) ----------
@extend_schema(tags=["profiles"])
class StudentProfileAdminViewSet(viewsets.ModelViewSet):
    """
    List/Detail: barcha teacher & superadmin ko'radi.
    PATCH /{id}/approve: is_approved ni o'zgartirish (audit yoziladi).
    PATCH /{id}/topup: balance'ga qo'shish (audit yoziladi).
    """

    permission_classes = [IsTeacherOrSuperAdmin]
    http_method_names = ["get", "patch", "head", "options"]
    queryset = (
        StudentProfile.objects.select_related("user")
        .only(
            "id",
            "balance",
            "is_approved",
            "type",
            "created_at",
            "updated_at",
            "user_id",
        )
        .order_by("-created_at")
    )
    serializer_class = StudentProfileReadSerializer

    @extend_schema(
        summary="Approve/disapprove student",
        request=StudentApproveSerializer,
        responses={200: StudentProfileReadSerializer},
    )
    @action(detail=True, methods=["patch"], url_path="approve")
    def approve(self, request, pk=None):
        instance = self.get_object()
        ser = StudentApproveSerializer(instance, data=request.data)
        ser.is_valid(raise_exception=True)
        profile = ser.save()

        # AUDIT
        note = (request.data.get("note") or "")[:255]
        StudentApprovalLog.objects.create(
            student=profile,
            approved=profile.is_approved,
            actor=request.user,
            note=note,
        )

        return Response(
            StudentProfileReadSerializer(profile).data, status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Top up balance",
        request=StudentTopUpSerializer,
        responses={200: StudentProfileReadSerializer},
    )
    @action(detail=True, methods=["patch"], url_path="topup")
    def topup(self, request, pk=None):
        instance = self.get_object()
        ser = StudentTopUpSerializer(data=request.data, context={"instance": instance})
        ser.is_valid(raise_exception=True)
        profile = ser.save()

        # AUDIT
        amount = ser.validated_data["amount"]
        note = (request.data.get("note") or "")[:255]
        StudentTopUpLog.objects.create(
            student=profile,
            amount=amount,
            new_balance=profile.balance,
            actor=request.user,
            note=note,
        )

        return Response(
            StudentProfileReadSerializer(profile).data, status=status.HTTP_200_OK
        )


# ---------- Admin-ish: Teacher profiles (read-only; teacher yoki superadmin) ----------
@extend_schema(tags=["profiles"])
class TeacherProfileAdminViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsTeacherOrSuperAdmin]
    queryset = (
        TeacherProfile.objects.select_related("user")
        .only("id", "created_at", "updated_at", "user_id")
        .order_by("-created_at")
    )
    serializer_class = TeacherProfileReadSerializer


# ---------- Superadmin-only: Audit logs ----------
class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "superadmin"
        )


@extend_schema(
    tags=["profiles"], summary="(Superadmin) Student approval logs list/retrieve"
)
class StudentApprovalLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    queryset = (
        StudentApprovalLog.objects.select_related("student", "actor")
        .only("id", "approved", "note", "created_at", "student_id", "actor_id")
        .order_by("-created_at")
    )
    serializer_class = StudentApprovalLogSerializer


@extend_schema(
    tags=["profiles"], summary="(Superadmin) Student top-up logs list/retrieve"
)
class StudentTopUpLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    queryset = (
        StudentTopUpLog.objects.select_related("student", "actor")
        .only(
            "id",
            "amount",
            "new_balance",
            "note",
            "created_at",
            "student_id",
            "actor_id",
        )
        .order_by("-created_at")
    )
    serializer_class = StudentTopUpLogSerializer
