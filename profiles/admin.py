from django.contrib import admin

from profiles.models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "id", "created_on")
    search_fields = ("full_name", "bio")
    readonly_fields = ("id", "created_on", "updated_on")
