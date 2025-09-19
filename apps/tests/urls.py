#  apps/tests/urls.py
from __future__ import annotations

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PublicTestViewSet,
    TestAdminViewSet,
    TestSectionAdminViewSet,
    QuestionAdminViewSet,
    QuestionChoiceAdminViewSet,
    WritingTaskAdminViewSet,
)

router = DefaultRouter()
# public
router.register(r"catalog/tests", PublicTestViewSet, basename="public-tests")

# admin/teacher
router.register(r"admin/tests", TestAdminViewSet, basename="admin-tests")
router.register(
    r"admin/sections", TestSectionAdminViewSet, basename="admin-testsections"
)
router.register(r"admin/questions", QuestionAdminViewSet, basename="admin-questions")
router.register(r"admin/choices", QuestionChoiceAdminViewSet, basename="admin-qchoices")
router.register(
    r"admin/writing-tasks", WritingTaskAdminViewSet, basename="admin-wtasks"
)

urlpatterns = [path("", include(router.urls))]
