# apps/profiles/models.py
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.users.models import User, UUIDPrimaryKeyMixin, TimeStampedMixin


# ---------- Student Profile ----------
class StudentProfile(UUIDPrimaryKeyMixin, TimeStampedMixin):
    TYPE_CHOICES = [("online", "Online"), ("offline", "Offline")]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile", unique=True
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    is_approved = models.BooleanField(default=False)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, null=True, blank=True)

    class Meta:
        db_table = "student_profiles"
        indexes = [
            # models.Index(fields=["user"]),  # keraksiz, OneToOne unique index bor
            models.Index(fields=["is_approved"]),
            models.Index(fields=["type"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(balance__gte=0),
                name="student_profile_balance_gte_0",
            ),
        ]

    def save(self, *args, **kwargs):
        self.type = "offline" if self.is_approved else "online"
        super().save(*args, **kwargs)


# ---------- Teacher Profile ----------
class TeacherProfile(UUIDPrimaryKeyMixin, TimeStampedMixin):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="teacher_profile", unique=True
    )

    class Meta:
        db_table = "teacher_profiles"
        # indexes = [models.Index(fields=["user"])]  # keraksiz
