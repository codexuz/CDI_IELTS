# apps/profiles/admin.py
from django.contrib import admin
from .models import StudentProfile, TeacherProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "is_approved", "balance", "created_at")
    list_filter = ("type", "is_approved")
    search_fields = ("user__fullname", "user__phone_number")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    search_fields = ("user__fullname", "user__phone_number")
    readonly_fields = ("created_at", "updated_at")
