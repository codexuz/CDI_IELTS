# apps/profiles/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    me,
    StudentProfileAdminViewSet,
    TeacherProfileAdminViewSet,
    StudentApprovalLogViewSet,
    StudentTopUpLogViewSet,
)

router = DefaultRouter()
router.register(
    r"admin/students", StudentProfileAdminViewSet, basename="admin-students"
)
router.register(
    r"admin/teachers", TeacherProfileAdminViewSet, basename="admin-teachers"
)
router.register(
    r"admin/logs/approvals", StudentApprovalLogViewSet, basename="logs-approvals"
)
router.register(r"admin/logs/topups", StudentTopUpLogViewSet, basename="logs-topups")

urlpatterns = [
    path("me/", me, name="profiles-me"),
    path("", include(router.urls)),
]
