from django.contrib import admin

from jobs.models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "location", "job_type", "remote_option", "created_on")
    list_filter = ("job_type", "remote_option")
    search_fields = ("title", "description", "location")
    readonly_fields = ("id", "created_on", "updated_on")
