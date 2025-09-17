# apps/users/urls.py
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def ping(_request):
    return Response({"status": "ok", "app": "users"})


urlpatterns = [
    path("ping/", ping, name="users-ping"),
]
