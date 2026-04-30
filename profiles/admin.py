from django.contrib import admin

from profiles.models import Preference, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "id", "created_on")
    search_fields = ("full_name", "bio")
    readonly_fields = ("id", "created_on", "updated_on")


@admin.register(Preference)
class PreferenceAdmin(admin.ModelAdmin):
    list_display = ("id", "profile", "title", "job_type", "remote_option", "created_on")
    list_filter = ("job_type", "remote_option")
    search_fields = ("title", "profile__full_name")
    autocomplete_fields = ("profile",)
    readonly_fields = ("id", "created_on", "updated_on")
