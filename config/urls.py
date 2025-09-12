# config/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    # API routes
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/users/", include("apps.users.urls")),
    # path("api/tests/", include("apps.tests.urls")),
    # path("api/user-tests/", include("apps.user_tests.urls")),
    # path("api/payments/", include("apps.payments.urls")),
    # path("api/teacher-checking/", include("apps.teacher_checking.urls")),
    # path("api/speaking/", include("apps.speaking.urls")),
    path("api/profiles/", include("apps.profiles.urls")),
    # OpenAPI schema & Swagger UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]

# Static & media (dev mode only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
