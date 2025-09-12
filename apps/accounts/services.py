from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import User


def issue_tokens(user: User) -> dict:
    """
    SimpleJWT orqali access/refresh tokenlar.
    """
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }
