#  apps/tests/views.py
from django.db.models import Count, Prefetch
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, mixins, permissions, filters

from apps.tests.models.ielts import Test
from apps.tests.models.listening import ListeningSection
from apps.tests.models.question import QuestionSet
from apps.tests.models.reading import ReadingPassage
from apps.tests.serializers import (
    TestListSerializer,
    TestDetailSerializer,
    QuestionSetSummarySerializer,
    QuestionSetDetailSerializer,
)

# Performance-friendly prefetch trees
LISTENING_PREFETCH = Prefetch(
    "listening__sections",
    queryset=ListeningSection.objects.all()
    .only("id", "name", "mp3_file")
    .prefetch_related("questions_set"),
)
READING_PREFETCH = Prefetch(
    "reading__passages",
    queryset=ReadingPassage.objects.all()
    .only("id", "name")
    .prefetch_related("questions_set"),
)


@extend_schema(
    tags=["Tests"],
    summary="IELTS testlari ro'yxati",
    description=(
        "Barcha mavjud testlar. `ordering` parametri qo'llab-quvvatlanadi "
        "(`created_at` yoki `title`)."
    ),
    parameters=[
        OpenApiParameter(
            name="ordering",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Masalan: `-created_at` yoki `title`",
        ),
    ],
)
class TestViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    Read-only ViewSet:
    - list: eng yengil serializer (TestListSerializer)
    - retrieve: to'liq nested detallari bilan (TestDetailSerializer)
    """

    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "title"]
    ordering = ["-created_at"]

    def get_queryset(self):
        # List uchun yengil prefetch; retrieve uchun to'liq
        qs = (
            Test.objects.all()
            .select_related("writing__task_one", "writing__task_two")
            .prefetch_related(LISTENING_PREFETCH, READING_PREFETCH)
        )
        if self.action == "list":
            return qs.only("id", "title", "price", "created_at")
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return TestListSerializer
        return TestDetailSerializer


@extend_schema(
    tags=["Tests"],
    summary="Question set ro'yxati (summary)",
    description="Har bir set uchun `questions_count` qaytaradi.",
)
class QuestionSetViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        base = QuestionSet.objects.all()
        if self.action == "list":
            return base.annotate(questions_count=Count("questions")).only("id", "name")
        # retrieve: to'liq savollar bilan
        return base.prefetch_related("questions")

    def get_serializer_class(self):
        return (
            QuestionSetSummarySerializer
            if self.action == "list"
            else QuestionSetDetailSerializer
        )
