from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.views import View

from core.views import SuperuserRequiredMixin
from jobs.consts import JobType
from jobs.models import Job


class JobListView(SuperuserRequiredMixin, View):
    def get(self, request):
        selected_job_type = request.GET.get("job_type") or ""
        q = request.GET.get("q", "").strip()
        qs = Job.objects.annotate(assessment_count=Count("assessments")).order_by(
            "-created_on"
        )
        if selected_job_type and selected_job_type in JobType.values:
            qs = qs.filter(job_type=selected_job_type)
        if q:
            qs = qs.filter(title__icontains=q)

        paginator = Paginator(qs, 20)
        jobs = paginator.get_page(request.GET.get("page", 1))
        result_count = paginator.count

        counts_rows = Job.objects.values("job_type").annotate(count=Count("id"))
        counts_by_type = {row["job_type"]: row["count"] for row in counts_rows}
        job_type_tabs = [
            {"value": value, "label": label, "count": counts_by_type.get(value, 0)}
            for value, label in JobType.choices
        ]
        total_count = Job.objects.count()

        context = {
            "jobs": jobs,
            "job_type_tabs": job_type_tabs,
            "selected_job_type": selected_job_type,
            "q": q,
            "result_count": result_count,
            "total_count": total_count,
        }
        return render(request, "jobs/list.html", context)


class JobDetailView(SuperuserRequiredMixin, View):
    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        assessments = list(
            job.assessments.select_related("preference__profile").order_by(
                "-created_on"
            )[:50]
        )
        return render(
            request,
            "jobs/detail.html",
            {
                "job": job,
                "assessments": assessments,
                "assessment_count": job.assessments.count(),
            },
        )
