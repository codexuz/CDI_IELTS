from __future__ import annotations
from typing import Iterable
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def _normalize_answer(s: str) -> str:
    return " ".join(s.strip().lower().split())


def validate_accepted_answers(value):
    """
    JSON list bo‘lishi va kamida bitta javob bo‘lishi shart.
    """
    if not isinstance(value, list) or not value:
        raise ValidationError(_("Accepted answers must be a non-empty list."))
    for v in value:
        if not isinstance(v, str) or not _normalize_answer(v):
            raise ValidationError(_("Each accepted answer must be a non-empty string."))


def validate_max_words(v: int):
    if v is None or v < 1:
        raise ValidationError(_("Expected max words must be >= 1."))
