from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from assessment.consts import Status
from assessment.models import Assessment
from assessment.tasks import reassess_assessment
from core.views import SuperuserRequiredMixin


class AssessmentListView(SuperuserRequiredMixin, View):
    def get(self, request):
        selected_status = request.GET.get("status") or ""
        qs = Assessment.objects.select_related("job", "preference__profile").order_by(
            "-created_on"
        )
        if selected_status and selected_status in Status.values:
            qs = qs.filter(status=selected_status)

        paginator = Paginator(qs, 20)
        assessments = paginator.get_page(request.GET.get("page", 1))

        counts_rows = Assessment.objects.values("status").annotate(count=Count("id"))
        counts_by_status = {row["status"]: row["count"] for row in counts_rows}
        status_tabs = [
            {"value": value, "label": label, "count": counts_by_status.get(value, 0)}
            for value, label in Status.choices
        ]
        total_count = sum(counts_by_status.values())

        context = {
            "assessments": assessments,
            "status_tabs": status_tabs,
            "selected_status": selected_status,
            "total_count": total_count,
        }
        return render(request, "assessments/list.html", context)


class AssessmentDetailView(SuperuserRequiredMixin, View):
    def _get(self, pk):
        return get_object_or_404(
            Assessment.objects.select_related("job", "preference__profile"), pk=pk
        )

    def _render(self, request, assessment):
        return render(
            request,
            "assessments/detail.html",
            {
                "assessment": assessment,
                "job": assessment.job,
                "preference": assessment.preference,
                "profile": assessment.preference.profile,
                "status_choices": Status.choices,
            },
        )

    def get(self, request, pk):
        return self._render(request, self._get(pk))

    def post(self, request, pk):
        assessment = self._get(pk)
        status = request.POST.get("status", "").strip()
        if status not in Status.values:
            messages.error(request, "Invalid status.")
            return self._render(request, assessment)
        assessment.status = status
        assessment.save(update_fields=["status", "updated_on"])
        messages.success(request, "Assessment updated.")
        return redirect("assessment_detail", pk=assessment.pk)


class AssessmentReassessView(SuperuserRequiredMixin, View):
    def post(self, request, pk):
        assessment = get_object_or_404(Assessment, pk=pk)
        reassess_assessment.delay(assessment.id)
        messages.success(request, "Re-assessment queued.")
        return redirect("assessment_detail", pk=assessment.pk)
