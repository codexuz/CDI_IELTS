from rest_framework import permissions


class IsTeacherOrSuperAdmin(permissions.BasePermission):
    """
    Faqat teacher yoki superadmin ruxsatiga ega bo'lsin (oddiy is_staff emas).
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.role in {"teacher", "superadmin"})
        )
