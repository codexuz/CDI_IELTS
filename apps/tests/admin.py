from django.contrib import admin

from .models import (
    Test,
    Listening,
    ListeningSection,
    Reading,
    ReadingPassage,
    Writing,
    TaskOne,
    TaskTwo,
    QuestionSet,
    Question,
)


class ListeningSectionInline(admin.TabularInline):
    model = Listening.sections.through
    extra = 0


class ReadingPassageInline(admin.TabularInline):
    model = Reading.passages.through
    extra = 0


class QuestionInline(admin.TabularInline):
    model = QuestionSet.questions.through
    extra = 0


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "updated_at")
    search_fields = ("title",)
    list_filter = ("created_at",)


@admin.register(Listening)
class ListeningAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "updated_at")
    inlines = [ListeningSectionInline]


@admin.register(ListeningSection)
class ListeningSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "id")
    filter_horizontal = ("questions_set",)


@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "updated_at")
    inlines = [ReadingPassageInline]


@admin.register(ReadingPassage)
class ReadingPassageAdmin(admin.ModelAdmin):
    list_display = ("name", "id")
    filter_horizontal = ("questions_set",)


@admin.register(Writing)
class WritingAdmin(admin.ModelAdmin):
    list_display = ("id", "task_one", "task_two")


@admin.register(TaskOne)
class TaskOneAdmin(admin.ModelAdmin):
    list_display = ("topic", "image_title")


@admin.register(TaskTwo)
class TaskTwoAdmin(admin.ModelAdmin):
    list_display = ("topic",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "text", "question_type")
    list_filter = ("question_type",)
    search_fields = ("text",)


@admin.register(QuestionSet)
class QuestionSetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )
    inlines = [QuestionInline]
    search_fields = ("name",)
