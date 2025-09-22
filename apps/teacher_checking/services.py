#  apps/teacher_checking/services.py
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.user_tests.models import UserTest, TestResult
from apps.users.models import User
from .models import TeacherSubmission


@transaction.atomic
def submit_writing(*, user_test: UserTest, task: str, text: str) -> TeacherSubmission:

    sub, created = TeacherSubmission.objects.get_or_create(
        user_test=user_test,
        task=task,
        defaults={"submitted_text": text, "status": TeacherSubmission.Status.REQUESTED},
    )
    if not created:
        if sub.status == TeacherSubmission.Status.CHECKED:
            raise ValidationError("This task is already checked.")
        sub.submitted_text = text
        sub.status = TeacherSubmission.Status.REQUESTED
        sub.teacher = None
        sub.score = None
        sub.feedback = ""
        sub.submitted_at = timezone.now()
        sub.save()
    return sub


@transaction.atomic
def claim_submission(*, submission_id, teacher: User) -> TeacherSubmission:
    """
    Concurrency-safe claim:
    SELECT ... FOR UPDATE SKIP LOCKED -> status=requested va teacher is null bo'lganini olamiz.
    """
    qs = TeacherSubmission.objects.select_for_update(skip_locked=True).filter(
        id=submission_id,
        status=TeacherSubmission.Status.REQUESTED,
        teacher__isnull=True,
    )
    sub = qs.first()
    if not sub:
        raise ValidationError(
            "Submission is already taken or not in 'requested' state."
        )
    sub.status = TeacherSubmission.Status.IN_CHECKING
    sub.teacher = teacher
    sub.save(update_fields=["status", "teacher", "updated_at"])
    return sub


@transaction.atomic
def grade_submission(
    *, submission_id, teacher: User, score: float, feedback: str
) -> TeacherSubmission:

    sub = (
        TeacherSubmission.objects.select_for_update()
        .select_related("user_test")
        .get(id=submission_id)
    )
    if sub.teacher_id and sub.teacher_id != teacher.id:
        raise ValidationError("This submission is assigned to another teacher.")
    if sub.status != TeacherSubmission.Status.IN_CHECKING:
        raise ValidationError("Submission must be in 'in_checking' state to grade.")

    sub.score = float(score)
    sub.feedback = feedback or ""
    sub.status = TeacherSubmission.Status.CHECKED
    sub.checked_at = timezone.now()
    sub.teacher = teacher
    sub.save()

    ut = sub.user_test
    tr, _ = TestResult.objects.get_or_create(user_test=ut)

    scores = list(
        TeacherSubmission.objects.filter(
            user_test=ut, status=TeacherSubmission.Status.CHECKED
        ).values_list("score", flat=True)
    )
    if scores:
        tr.writing_score = round(sum(scores) / len(scores), 1)
        comps = [
            x
            for x in [tr.listening_score, tr.reading_score, tr.writing_score]
            if x is not None
        ]
        tr.overall_score = round(sum(comps) / len(comps), 1) if comps else None
        tr.save(update_fields=["writing_score", "overall_score", "updated_at"])

    return sub
