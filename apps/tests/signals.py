#  apps/tests/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import (
    Test,
    Listening,
    ListeningSection,
    Reading,
    ReadingPassage,
    Writing,
    TaskOne,
    TaskTwo,
)


@receiver(post_save, sender=Test)
def create_sections_for_test(sender, instance: Test, created, **kwargs):
    if not created:
        return

    listening = Listening.objects.create(title=f"{instance.title} Listening")
    for i in range(1, 5):
        section = ListeningSection.objects.create(
            name=f"Section {i} for {instance.title}"
        )
        listening.sections.add(section)

    reading = Reading.objects.create(title=f"{instance.title} Reading")
    for i in range(1, 4):
        passage = ReadingPassage.objects.create(
            name=f"Passage {i} for {instance.title}", passage=""
        )
        reading.passages.add(passage)


    task_two = TaskTwo.objects.create(topic=f"{instance.title} Task Two")
    task_one = TaskOne.objects.create(
        topic=f"{instance.title} Task One",
        image_title="",
        image="",
    )
    writing = Writing.objects.create(task_one=task_one, task_two=task_two)

    Test.objects.filter(pk=instance.pk).update(
        listening=listening, reading=reading, writing=writing
    )
