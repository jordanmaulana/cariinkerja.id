from django.contrib import admin

from assessment.models import Assessment


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("id", "preference", "job", "score", "created_on")
    list_filter = ("score",)
    search_fields = ("preference__profile__full_name", "job__title")
    readonly_fields = ("id", "created_on", "updated_on")
    autocomplete_fields = ("preference", "job")
