#  apps/tests/views.py
from __future__ import annotations

from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Test, TestSection, Question, QuestionChoice, WritingTask
from .serializers import (
    # public
    TestListSerializer,
    TestDetailSerializer,
    # admin
    TestAdminSerializer,
    TestSectionAdminSerializer,
    QuestionAdminSerializer,
    QuestionChoiceAdminSerializer,
    WritingTaskAdminSerializer,
)


# ---------- Permission helpers ----------
class IsTeacherOrSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        u = getattr(request, "user", None)
        return bool(
            u
            and u.is_authenticated
            and getattr(u, "role", None) in {"teacher", "superadmin"}
        )


# =====================
# Public (read-only)
# =====================
@extend_schema(tags=["tests"])
class PublicTestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Barcha foydalanuvchilar (hatto anon) uchun testlar katalogi.
    Detailda to‘liq tarkib, lekin LR uchun `is_correct` yo‘q.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = TestListSerializer
    lookup_field = "id"

    def get_queryset(self):
        qs = (
            Test.objects.filter(is_active=True)
            .only(
                "id",
                "number",
                "title",
                "price",
                "is_active",
                "created_at",
                "updated_at",
            )
            .order_by("-created_at")
        )
        return qs

    def get_serializer_class(self):
        return TestDetailSerializer if self.action == "retrieve" else TestListSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="q", description="Search in title/number", required=False, type=str
            ),
            OpenApiParameter(
                name="min_price",
                description="Minimal price",
                required=False,
                type=float,
            ),
            OpenApiParameter(
                name="max_price", description="Max price", required=False, type=float
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        q = request.query_params.get("q")
        mn = request.query_params.get("min_price")
        mx = request.query_params.get("max_price")

        if q:
            term = q.strip()
            qs = qs.filter(Q(title__icontains=term) | Q(number__icontains=term))
        try:
            if mn is not None:
                qs = qs.filter(price__gte=float(mn))
            if mx is not None:
                qs = qs.filter(price__lte=float(mx))
        except ValueError:
            pass

        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page if page is not None else qs, many=True)
        return (
            self.get_paginated_response(ser.data)
            if page is not None
            else Response(ser.data)
        )


# ============================
# Admin/Teacher (full control)
# ============================
@extend_schema(tags=["tests"])
class TestAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTeacherOrSuperAdmin]
    queryset = (
        Test.objects.all()
        .only(
            "id",
            "number",
            "title",
            "description",
            "price",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        )
        .order_by("-created_at")
    )
    serializer_class = TestAdminSerializer

    @action(detail=True, methods=["get"], url_path="sections")
    def list_sections(self, request, pk=None):
        test = self.get_object()
        qs = test.sections.only(
            "id", "test_id", "section_type", "order", "created_at", "updated_at"
        ).order_by("order")
        ser = TestSectionAdminSerializer(qs, many=True)
        return Response(ser.data, status=status.HTTP_200_OK)


@extend_schema(tags=["tests"])
class TestSectionAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTeacherOrSuperAdmin]
    queryset = (
        TestSection.objects.all()
        .only("id", "test_id", "section_type", "order", "created_at", "updated_at")
        .order_by("test_id", "order")
    )
    serializer_class = TestSectionAdminSerializer


@extend_schema(tags=["tests"])
class QuestionAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTeacherOrSuperAdmin]
    queryset = (
        Question.objects.select_related(
            "part", "part__section", "part__section__test"
        ).only(
            "id",
            "question_type",
            "text",
            "media_file",
            "media_url",
            "metadata",
            "order",
            "part_id",
            "part__section_id",
            "part__section__section_type",
            "part__section__order",
            "part__section__test__number",
            "created_at",
            "updated_at",
        )
        # Kengroq tartib: Test raqami → Section tartibi → Part raqami → Savol tartibi
        .order_by(
            "part__section__test__number",
            "part__section__order",
            "part__part_number",
            "order",
        )
    )
    serializer_class = QuestionAdminSerializer


@extend_schema(tags=["tests"])
class QuestionChoiceAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTeacherOrSuperAdmin]
    queryset = (
        QuestionChoice.objects.select_related("question")
        .only(
            "id",
            "question_id",
            "order",
            "text",
            "is_correct",
            "created_at",
            "updated_at",
        )
        .order_by("question_id", "order")
    )
    serializer_class = QuestionChoiceAdminSerializer


@extend_schema(tags=["tests"])
class WritingTaskAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTeacherOrSuperAdmin]
    queryset = (
        WritingTask.objects.select_related("section")
        .only(
            "id",
            "section_id",
            "task_number",
            "question_text",
            "media_url",
            "created_at",
            "updated_at",
        )
        .order_by("section_id", "task_number")
    )
    serializer_class = WritingTaskAdminSerializer
