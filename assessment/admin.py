from django.contrib import admin

from assessment.models import Assessment


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("id", "profile", "job", "score", "created_on")
    list_filter = ("score",)
    search_fields = ("profile__full_name", "job__title")
    readonly_fields = ("id", "created_on", "updated_on")
    autocomplete_fields = ("profile", "job")
