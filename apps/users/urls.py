#  apps/users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ping, MeView, UserAdminViewSet

router = DefaultRouter()
router.register(r"admin/users", UserAdminViewSet, basename="admin-users")

urlpatterns = [
    path("ping/", ping, name="users-ping"),
    path("me/", MeView.as_view(), name="users-me"),
    path("", include(router.urls)),
]
