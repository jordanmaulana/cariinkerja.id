import json
import logging
import smtplib
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models import Avg, Count, Max, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from assessment.models import Assessment
from assessment.tasks import crawl_and_assess_preference
from billing.forms import PlanForm
from billing.models import Plan, Subscription, SubscriptionStatus
from core.forms import SmtpTestForm
from core.notifications.email import send_email
from core.realtime import publish, user_channel
from jobs.models import Job
from jobs.scrapers import scraper_for_url
from profiles.consts import Status
from profiles.models import Preference, Profile

logger = logging.getLogger(__name__)


class SuperuserRequiredMixin(View):
    @method_decorator(
        user_passes_test(lambda user: user.is_superuser, login_url="/login/")
    )
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class AdminLoginView(LoginView):
    template_name = "registration/login.html"
    success_url = "/dashboard/"


class DashboardView(SuperuserRequiredMixin, View):
    def get(self, request):
        today = timezone.localdate()
        now = timezone.now()
        cache_key = f"dashboard_stats_v2_{today}_{request.GET.get('page', 1)}"
        cached = cache.get(cache_key)
        if cached:
            return render(request, "dashboard.html", cached)

        thirty_days_ago = today - timedelta(days=29)

        profile_stats = Profile.objects.aggregate(
            profile_count=Count("id"),
            profiles_today=Count("id", filter=Q(created_on__date=today)),
        )
        job_stats = Job.objects.aggregate(
            job_count=Count("id"),
            jobs_today=Count("id", filter=Q(created_on__date=today)),
        )
        assessment_stats = Assessment.objects.aggregate(
            assessment_count=Count("id"),
            assessments_today=Count("id", filter=Q(created_on__date=today)),
            avg_score=Avg("score"),
            bucket_low=Count("id", filter=Q(score__lte=25)),
            bucket_mid_low=Count("id", filter=Q(score__gt=25, score__lte=50)),
            bucket_mid_high=Count("id", filter=Q(score__gt=50, score__lte=75)),
            bucket_high=Count("id", filter=Q(score__gt=75)),
        )

        recent_qs = Assessment.objects.select_related(
            "job", "preference__profile"
        ).order_by("-created_on")
        paginator = Paginator(recent_qs, 10)
        recent_assessments = paginator.get_page(request.GET.get("page", 1))

        top_profiles = (
            Profile.objects.filter(
                preferences__assessments__created_on__date__gte=thirty_days_ago
            )
            .annotate(
                assessment_count=Count("preferences__assessments"),
                best_score=Max("preferences__assessments__score"),
            )
            .order_by("-best_score", "-assessment_count")[:10]
        )

        per_day = (
            Assessment.objects.filter(created_on__date__range=[thirty_days_ago, today])
            .extra({"date": "date(created_on)"})
            .values("date")
            .annotate(count=Count("id"))
        )
        counts = {row["date"]: row["count"] for row in per_day}
        date_range = [thirty_days_ago + timedelta(days=i) for i in range(30)]
        daily_assessments = [counts.get(str(d), counts.get(d, 0)) for d in date_range]
        date_labels = [d.strftime("%Y-%m-%d") for d in date_range]

        avg_score = assessment_stats["avg_score"]
        avg_score_display = round(avg_score, 1) if avg_score is not None else 0

        # Operator attention — what needs my action right now?
        pref_pipeline_rows = Preference.objects.values("status").annotate(c=Count("id"))
        preference_pipeline = {row["status"]: row["c"] for row in pref_pipeline_rows}
        waiting_admin = preference_pipeline.get(Status.WAITING_ADMIN, 0)
        waiting_payment = preference_pipeline.get(Status.WAITING_PAYMENT, 0)
        running_prefs = preference_pipeline.get(Status.RUNNING, 0)
        expired_prefs = preference_pipeline.get(Status.EXPIRED, 0)
        pref_pipeline_total = (
            waiting_payment + waiting_admin + running_prefs + expired_prefs
        )

        pending_payments = Subscription.objects.filter(
            status=SubscriptionStatus.PENDING
        ).count()
        expiring_soon = Subscription.objects.filter(
            status=SubscriptionStatus.ACTIVE,
            expires_at__lte=now + timedelta(days=7),
            expires_at__gt=now,
        ).count()
        linkedin_gate_failed = (
            Profile.objects.filter(linkedin_quality_ok=False)
            .exclude(linkedin_raw="")
            .count()
        )

        # Billing pulse — is the business healthy?
        active_subs_qs = Subscription.objects.filter(
            status=SubscriptionStatus.ACTIVE,
            expires_at__gt=now,
        )
        billing = active_subs_qs.aggregate(
            active_subs=Count("id"),
            mrr=Sum("amount_paid"),
        )
        active_subs = billing["active_subs"] or 0
        mrr = billing["mrr"] or 0

        month_start = today.replace(day=1)
        paid_this_month = (
            Subscription.objects.filter(
                started_at__date__gte=month_start,
                status__in=[
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.EXPIRED,
                    SubscriptionStatus.REPLACED,
                ],
            ).aggregate(total=Sum("amount_paid"))["total"]
            or 0
        )

        sub_per_day_rows = (
            Subscription.objects.filter(
                started_at__date__range=[thirty_days_ago, today],
                status__in=[
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.EXPIRED,
                    SubscriptionStatus.REPLACED,
                ],
            )
            .extra({"date": "date(started_at)"})
            .values("date")
            .annotate(count=Count("id"))
        )
        sub_counts = {row["date"]: row["count"] for row in sub_per_day_rows}
        daily_subs = [sub_counts.get(str(d), sub_counts.get(d, 0)) for d in date_range]

        latest_subs = list(
            Subscription.objects.select_related("profile", "plan").order_by(
                "-created_on"
            )[:5]
        )

        context = {
            **profile_stats,
            **job_stats,
            **assessment_stats,
            "avg_score_display": avg_score_display,
            "recent_assessments": recent_assessments,
            "top_profiles": top_profiles,
            "daily_assessments_json": json.dumps(daily_assessments),
            "date_labels_json": json.dumps(date_labels),
            "daily_subs_json": json.dumps(daily_subs),
            # Operator attention
            "waiting_admin": waiting_admin,
            "waiting_payment_count": waiting_payment,
            "running_prefs": running_prefs,
            "expired_prefs": expired_prefs,
            "pref_pipeline_total": pref_pipeline_total,
            "pending_payments": pending_payments,
            "expiring_soon": expiring_soon,
            "linkedin_gate_failed": linkedin_gate_failed,
            # Billing
            "active_subs": active_subs,
            "mrr": mrr,
            "paid_this_month": paid_this_month,
            "latest_subs": latest_subs,
            "now": now,
        }
        cache.set(cache_key, context, 300)
        return render(request, "dashboard.html", context)


class PreferenceListView(SuperuserRequiredMixin, View):
    def get(self, request):
        selected_status = request.GET.get("status") or ""
        qs = Preference.objects.select_related("profile").order_by("-created_on")
        if selected_status and selected_status in Status.values:
            qs = qs.filter(status=selected_status)

        paginator = Paginator(qs, 20)
        preferences = paginator.get_page(request.GET.get("page", 1))

        counts_rows = Preference.objects.values("status").annotate(count=Count("id"))
        counts_by_status = {row["status"]: row["count"] for row in counts_rows}
        status_tabs = [
            {"value": value, "label": label, "count": counts_by_status.get(value, 0)}
            for value, label in Status.choices
        ]
        total_count = sum(counts_by_status.values())

        context = {
            "preferences": preferences,
            "status_tabs": status_tabs,
            "selected_status": selected_status,
            "total_count": total_count,
        }
        return render(request, "preferences/list.html", context)


class PreferenceDetailView(SuperuserRequiredMixin, View):
    def _get(self, pk):
        return get_object_or_404(
            Preference.objects.select_related("profile__user"), pk=pk
        )

    def _render(self, request, pref):
        return render(
            request,
            "preferences/detail.html",
            {
                "preference": pref,
                "profile": pref.profile,
                "status_choices": Status.choices,
                "crawl_urls_text": "\n".join(pref.crawl_urls or []),
            },
        )

    def get(self, request, pk):
        pref = self._get(pk)
        return self._render(request, pref)

    def post(self, request, pk):
        pref = self._get(pk)
        raw_urls = request.POST.get("crawl_urls", "")
        urls = [line.strip() for line in raw_urls.splitlines() if line.strip()]
        status = request.POST.get("status", "").strip()
        override_quality = request.POST.get("override_quality_gate") == "1"

        validator = URLValidator()
        for url in urls:
            try:
                validator(url)
            except ValidationError:
                messages.error(request, f"Invalid URL: {url}")
                return self._render(request, pref)
            if scraper_for_url(url)[0] is None:
                messages.error(
                    request,
                    f"No scraper available for URL: {url}",
                )
                return self._render(request, pref)

        if status not in Status.values:
            messages.error(request, "Invalid status.")
            return self._render(request, pref)

        moving_to_running = pref.status != Status.RUNNING and status == Status.RUNNING
        if (
            moving_to_running
            and not pref.profile.linkedin_quality_ok
            and not override_quality
        ):
            reason = pref.profile.linkedin_quality_reason or "no reason recorded"
            messages.error(
                request,
                f"LinkedIn marked sparse: {reason}. Re-ingest the profile or "
                "tick 'Override quality gate' to proceed.",
            )
            return self._render(request, pref)

        with transaction.atomic():
            pref.crawl_urls = urls
            pref.status = status
            pref.save(
                update_fields=[
                    "crawl_urls",
                    "status",
                    "updated_on",
                ]
            )

        user_id = getattr(getattr(pref.profile, "user", None), "id", None)
        if user_id is not None:
            publish(
                user_channel(user_id),
                {
                    "event": "preference.status_changed",
                    "preference_id": pref.id,
                    "status": pref.status,
                },
            )

        messages.success(request, "Preference updated.")
        return redirect("preference_detail", pk=pref.pk)


class PreferenceCrawlNowView(SuperuserRequiredMixin, View):
    def post(self, request, pk):
        pref = get_object_or_404(Preference, pk=pk)
        if not pref.crawl_urls:
            messages.error(
                request,
                "Preference has no crawl_urls — fill them first.",
            )
        else:
            crawl_and_assess_preference.delay(pref.id)
            messages.success(request, f"Queued crawl + assessment for {pref}.")
        return redirect("preference_detail", pk=pref.pk)


class PlanListView(SuperuserRequiredMixin, View):
    def get(self, request):
        qs = Plan.objects.all().order_by("price")
        paginator = Paginator(qs, 25)
        plans = paginator.get_page(request.GET.get("page", 1))
        return render(request, "plans/list.html", {"plans": plans})


class PlanCreateView(SuperuserRequiredMixin, View):
    def get(self, request):
        return render(
            request,
            "plans/form.html",
            {"form": PlanForm(), "title": "New plan", "plan": None},
        )

    def post(self, request):
        form = PlanForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "plans/form.html",
                {"form": form, "title": "New plan", "plan": None},
            )
        plan = form.save()
        messages.success(request, f"Created plan: {plan.name}.")
        return redirect("plan_list")


class PlanUpdateView(SuperuserRequiredMixin, View):
    def get(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        return render(
            request,
            "plans/form.html",
            {"form": PlanForm(instance=plan), "title": "Edit plan", "plan": plan},
        )

    def post(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        form = PlanForm(request.POST, instance=plan)
        if not form.is_valid():
            return render(
                request,
                "plans/form.html",
                {"form": form, "title": "Edit plan", "plan": plan},
            )
        form.save()
        messages.success(request, f"Updated plan: {plan.name}.")
        return redirect("plan_list")


class PlanDeleteView(SuperuserRequiredMixin, View):
    def post(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        if plan.subscriptions.exists():
            messages.error(
                request,
                "Cannot delete plan with existing subscriptions. Deactivate instead.",
            )
            return redirect("plan_list")
        plan.delete()
        messages.success(request, "Plan deleted.")
        return redirect("plan_list")


class SubscriptionListView(SuperuserRequiredMixin, View):
    def get(self, request):
        selected_status = request.GET.get("status") or ""
        qs = Subscription.objects.select_related("plan", "profile").order_by(
            "-created_on"
        )
        if selected_status and selected_status in SubscriptionStatus.values:
            qs = qs.filter(status=selected_status)

        paginator = Paginator(qs, 20)
        subscriptions = paginator.get_page(request.GET.get("page", 1))

        counts_rows = Subscription.objects.values("status").annotate(count=Count("id"))
        counts_by_status = {row["status"]: row["count"] for row in counts_rows}
        status_tabs = [
            {"value": value, "label": label, "count": counts_by_status.get(value, 0)}
            for value, label in SubscriptionStatus.choices
        ]
        total_count = sum(counts_by_status.values())

        return render(
            request,
            "subscriptions/list.html",
            {
                "subscriptions": subscriptions,
                "status_tabs": status_tabs,
                "selected_status": selected_status,
                "total_count": total_count,
            },
        )


class SubscriptionDetailView(SuperuserRequiredMixin, View):
    def _get(self, pk):
        return get_object_or_404(
            Subscription.objects.select_related("plan", "profile"), pk=pk
        )

    def get(self, request, pk):
        sub = self._get(pk)
        return render(
            request,
            "subscriptions/detail.html",
            {"subscription": sub, "status_choices": SubscriptionStatus.choices},
        )

    def post(self, request, pk):
        sub = self._get(pk)
        action = request.POST.get("action", "")
        now = timezone.now()
        if action == "activate":
            sub.status = SubscriptionStatus.ACTIVE
            sub.started_at = sub.started_at or now
            sub.expires_at = now + timedelta(days=30)
            sub.payment_provider = sub.payment_provider or "manual"
            sub.save(
                update_fields=[
                    "status",
                    "started_at",
                    "expires_at",
                    "payment_provider",
                    "updated_on",
                ]
            )
            messages.success(request, "Subscription activated.")
        elif action == "expire":
            sub.status = SubscriptionStatus.EXPIRED
            sub.save(update_fields=["status", "updated_on"])
            messages.success(request, "Subscription marked expired.")
        elif action == "cancel":
            sub.status = SubscriptionStatus.CANCELLED
            sub.save(update_fields=["status", "updated_on"])
            messages.success(request, "Subscription cancelled.")
        else:
            messages.error(request, "Unknown action.")
        return redirect("subscription_detail", pk=sub.pk)


class SmtpTestView(SuperuserRequiredMixin, View):
    template_name = "settings/smtp_test.html"

    def _context(self, form):
        return {
            "form": form,
            "config": {
                "host": settings.EMAIL_HOST or "(unset)",
                "port": settings.EMAIL_PORT,
                "user": settings.EMAIL_HOST_USER or "(unset)",
                "use_ssl": settings.EMAIL_USE_SSL,
                "use_tls": settings.EMAIL_USE_TLS,
                "from": settings.DEFAULT_FROM_EMAIL,
                "configured": bool(
                    settings.EMAIL_HOST
                    and settings.EMAIL_HOST_USER
                    and settings.EMAIL_HOST_PASSWORD
                ),
            },
        }

    def get(self, request):
        return render(request, self.template_name, self._context(SmtpTestForm()))

    def post(self, request):
        form = SmtpTestForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, self._context(form))

        to = form.cleaned_data["to"]
        try:
            sent = send_email(
                subject=form.cleaned_data["subject"],
                to=[to],
                body=form.cleaned_data["body"],
            )
        except (smtplib.SMTPException, OSError) as exc:
            logger.exception("smtp test failed")
            messages.error(request, f"Send failed: {exc.__class__.__name__}: {exc}")
            return render(request, self.template_name, self._context(form))

        if sent:
            messages.success(request, f"Sent test email to {to}.")
        else:
            messages.warning(request, "send() returned 0 — check SMTP env vars.")
        return redirect("smtp_test")
