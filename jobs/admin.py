from django.contrib import admin

from jobs.models import Job, SkillMapPage, SkillMapSnapshot
from jobs.skill_map import refresh_page


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "location",
        "job_type",
        "remote_option",
        "created_on",
    )
    list_filter = ("job_type", "remote_option")
    search_fields = ("title", "company", "description", "location")
    readonly_fields = ("id", "created_on", "updated_on")


@admin.register(SkillMapPage)
class SkillMapPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "min_jobs", "latest_job_count")
    list_filter = ("is_published",)
    search_fields = ("title", "slug", "match_words")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("id", "created_on", "updated_on")
    actions = ["refresh_now"]

    @admin.display(description="jobs (latest)")
    def latest_job_count(self, obj):
        snap = obj.latest_snapshot()
        return snap.job_count if snap else "—"

    @admin.action(description="Refresh snapshot now")
    def refresh_now(self, request, queryset):
        counts = [f"{p.slug}: {refresh_page(p).job_count}" for p in queryset]
        self.message_user(request, "Refreshed — " + ", ".join(counts))


@admin.register(SkillMapSnapshot)
class SkillMapSnapshotAdmin(admin.ModelAdmin):
    list_display = ("page", "computed_on", "job_count", "window_days")
    list_filter = ("page",)
    readonly_fields = ("id", "page", "computed_on", "window_days", "job_count", "data")
