from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .listening import Listening
from .reading import Reading
from .writing import Writing


class Test(models.Model):
    title = models.CharField(max_length=255)
    writing = models.ForeignKey(
        Writing, on_delete=models.CASCADE, null=True, blank=True
    )
    listening = models.ForeignKey(
        Listening, on_delete=models.CASCADE, null=True, blank=True
    )
    reading = models.ForeignKey(
        Reading, on_delete=models.CASCADE, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "test_table"
        verbose_name_plural = _("Tests")
        verbose_name = _("Test")
        ordering = ["created_at"]

    def __str__(self):
        return self.title

    def clean(self):
        if not self.pk:
            return
        # After object exists, enforce that relations must exist
        if self.writing is None:
            raise ValidationError("Writing must be defined")
        if self.listening is None:
            raise ValidationError("Listening must be defined")
        if self.reading is None:
            raise ValidationError("Reading must be defined")
