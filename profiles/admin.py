from django.contrib import admin

from profiles.models import Preference, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "id",
        "open_to_work",
        "linkedin_quality_ok",
        "whitelist",
        "created_on",
    )
    list_editable = ("whitelist",)
    list_filter = ("open_to_work", "linkedin_quality_ok", "whitelist")
    search_fields = ("full_name", "bio")
    readonly_fields = (
        "id",
        "created_on",
        "updated_on",
        "linkedin_ingested_at",
        "open_to_work",
        "linkedin_quality_ok",
        "linkedin_quality_reason",
    )


@admin.register(Preference)
class PreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "profile",
        "title",
        "job_type",
        "remote_option",
        "status",
        "created_on",
    )
    list_filter = ("status",)
    search_fields = ("title", "profile__full_name")
    autocomplete_fields = ("profile",)
    readonly_fields = ("id", "created_on", "updated_on")
