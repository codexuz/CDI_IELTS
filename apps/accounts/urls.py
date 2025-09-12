from django.urls import path
from .views import (
    RegisterStartView,
    RegisterVerifyView,
    LoginVerifyView,
    OtpIngestView,
)

urlpatterns = [
    path("register/start/", RegisterStartView.as_view()),
    path("register/verify/", RegisterVerifyView.as_view()),
    path("login/verify/", LoginVerifyView.as_view()),
    path("otp/ingest/", OtpIngestView.as_view()),  # Bot POST qiladi
]
