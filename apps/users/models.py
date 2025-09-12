# apps/users/models.py
import uuid
from typing import Optional

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
    Group,
    Permission,
)
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


# ---------- Reusable mixins ----------
class UUIDPrimaryKeyMixin(models.Model):
    """UUID primary key for all main tables."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedMixin(models.Model):
    """Created/Updated timestamps with sane defaults."""

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------- User Manager ----------
class UserManager(BaseUserManager):
    phone_validator = RegexValidator(
        regex=r"^\+?[1-9]\d{7,14}$",
        message="Phone must be in international format, e.g. +998901234567",
    )

    def _normalize_phone(self, phone: str) -> str:
        phone = (phone or "").strip().replace(" ", "")
        self.phone_validator(phone)
        return phone

    def create_user(
        self,
        fullname: str,
        phone_number: str,
        role: str,
        password: Optional[str] = None,
        **extra_fields,
    ):
        if not fullname:
            raise ValueError("Fullname is required")
        if not phone_number:
            raise ValueError("Phone number is required")
        if role not in {"superadmin", "student", "teacher"}:
            raise ValueError("Invalid role")

        user = self.model(
            fullname=fullname.strip(),
            phone_number=self._normalize_phone(phone_number),
            role=role,
            **extra_fields,
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        fullname: str,
        phone_number: str,
        password: Optional[str] = None,
        **extra_fields,
    ):
        # Agar manage.py createsuperuser `role` yuborsa — olib tashlaymiz
        extra_fields.pop("role", None)

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(
            fullname=fullname,
            phone_number=phone_number,
            role="superadmin",
            password=password,
            **extra_fields,
        )


# ---------- User ----------
class User(UUIDPrimaryKeyMixin, TimeStampedMixin, AbstractBaseUser, PermissionsMixin):
    class Roles(models.TextChoices):
        SUPERADMIN = "superadmin", "Superadmin"
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"

    fullname = models.CharField(max_length=100)

    # Telegram identifiers
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    telegram_username = models.CharField(
        max_length=50, unique=True, null=True, blank=True
    )

    phone_number = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=Roles.choices)

    # Django flags
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    last_activity = models.DateTimeField(null=True, blank=True, db_index=True)

    # PermissionsMixin fields with safe related_names
    groups = models.ManyToManyField(Group, related_name="cdi_users", blank=True)
    user_permissions = models.ManyToManyField(
        Permission, related_name="cdi_user_perms", blank=True
    )

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["fullname"]  # role endi so‘ralmaydi, superadmin fix

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["role"]),
            models.Index(fields=["telegram_id"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(fullname=""),
                name="users_fullname_not_empty",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.fullname} ({self.phone_number})"

    def update_last_activity(self):
        self.last_activity = timezone.now()
        self.save(update_fields=["last_activity"])
