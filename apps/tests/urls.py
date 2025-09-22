# apps/tests/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.tests.views import TestViewSet, QuestionSetViewSet

router = DefaultRouter()
router.register(r"tests", TestViewSet, basename="tests")
router.register(r"question-sets", QuestionSetViewSet, basename="question-sets")

urlpatterns = [
    path("", include(router.urls)),
]
