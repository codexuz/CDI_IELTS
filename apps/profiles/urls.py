# apps/profiles/urls.py
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    data = {
        "user": {
            "id": str(u.id),
            "fullname": u.fullname,
            "phone_number": u.phone_number,
            "role": u.role,
            "telegram_id": u.telegram_id,
            "telegram_username": u.telegram_username,
        },
        "student_profile": None,
        "teacher_profile": None,
    }
    sp = getattr(u, "student_profile", None)
    if sp:
        data["student_profile"] = {
            "balance": str(sp.balance),
            "is_approved": sp.is_approved,
            "type": sp.type,
            "created_at": sp.created_at,
        }
    tp = getattr(u, "teacher_profile", None)
    if tp:
        data["teacher_profile"] = {
            "created_at": tp.created_at,
        }
    return Response(data)


urlpatterns = [
    path("me/", me),  # GET /api/profiles/me/  (JWT kerak)
]
