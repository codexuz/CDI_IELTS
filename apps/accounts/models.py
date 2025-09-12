#  apps/accounts/models.py
import uuid
from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone


class VerificationCodeQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(consumed=False, expires_at__gt=timezone.now())

    def latest_alive_for(self, telegram_id=None, telegram_username=None, purpose=None):
        qs = self.alive()
        if telegram_id is not None:
            qs = qs.filter(telegram_id=telegram_id)
        if telegram_username is not None:
            qs = qs.filter(telegram_username=telegram_username)
        if purpose is not None:
            qs = qs.filter(purpose=purpose)
        return qs.order_by("-created_at").first()


class VerificationCodeManager(models.Manager.from_queryset(VerificationCodeQuerySet)):
    def issue(
        self,
        *,
        telegram_id: int,
        telegram_username: str | None,
        code: str,
        purpose: str,
        ttl_minutes: int = 2
    ):
        """
        Botdan kelgan kodni saqlaydi. Eski kodlarni o'chirmaymiz (audit), faqat
        tekshirayotganda eng so'nggi yaroqli kodni qabul qilamiz.
        """
        expires = timezone.now() + timedelta(minutes=ttl_minutes)
        return self.create(
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            code=code,
            purpose=purpose,
            expires_at=expires,
        )


class VerificationCode(models.Model):
    class Purpose(models.TextChoices):
        REGISTER = "register", "Register"
        LOGIN = "login", "Login"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    telegram_id = models.BigIntegerField(db_index=True, null=True)  # TEMP: null=True

    telegram_username = models.CharField(
        max_length=50, null=True, blank=True, db_index=True
    )

    code = models.CharField(max_length=6)
    purpose = models.CharField(
        max_length=10, choices=Purpose.choices, null=True
    )  # TEMP: null=True

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField()
    consumed = models.BooleanField(default=False, db_index=True)

    objects = VerificationCodeManager()

    class Meta:
        db_table = "verification_codes"
        indexes = [
            models.Index(fields=["telegram_id", "created_at"]),
            models.Index(fields=["purpose", "created_at"]),
            models.Index(fields=["expires_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(code__regex=r"^\d{6}$"),
                name="verification_code_six_digits",
            )
        ]

    def is_valid(self, raw_code: str) -> bool:
        now = timezone.now()
        return (
            (not self.consumed) and (self.code == raw_code) and (now < self.expires_at)
        )

    @transaction.atomic
    def consume(self):
        if not self.consumed:
            self.consumed = True
            self.save(update_fields=["consumed"])
