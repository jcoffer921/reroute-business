import csv
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from datetime import timedelta

from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.contrib import messages

from reroute_business.job_list.models import Job, Application
from reroute_business.profiles.models import EmployerProfile, UserProfile
from reroute_business.reentry_org.models import ReentryOrganization
from reroute_business.resources.models import Module

from .forms import (
    EmployerNotesForm,
    EmployerProfileForm,
    JobForm,
    JobReviewForm,
    ModuleForm,
    ReentryOrganizationForm,
    UserNoteForm,
)
from .models import AuditLog


def _log_action(actor, action, obj, metadata=None):
    AuditLog.objects.create(
        actor=actor,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=str(obj.pk),
        object_repr=str(obj),
        metadata=metadata or {},
    )


class StaffRequiredMixin:
    @method_decorator(staff_member_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


def _normalize_zip(value):
    raw = "".join(ch for ch in (value or "") if ch.isdigit())
    if len(raw) >= 5:
        return raw[:5]
    return None


def _zip_counts_from_values(values):
    counts = defaultdict(int)
    for value in values:
        zip_code = _normalize_zip(value)
        if zip_code:
            counts[zip_code] += 1
    return dict(counts)


def _zip_employer_counts():
    by_zip = defaultdict(set)
    for zip_code, employer_id in Job.objects.filter(is_active=True).values_list("zip_code", "employer_id"):
        normalized = _normalize_zip(zip_code)
        if normalized and employer_id:
            by_zip[normalized].add(employer_id)
    return {zip_code: len(employer_ids) for zip_code, employer_ids in by_zip.items()}


def _coverage_dataset():
    users_by_zip = _zip_counts_from_values(UserProfile.objects.values_list("zip_code", flat=True))
    jobs_by_zip = _zip_counts_from_values(Job.objects.filter(is_active=True).values_list("zip_code", flat=True))
    resources_by_zip = _zip_counts_from_values(ReentryOrganization.objects.values_list("zip_code", flat=True))

    zip_rows = []
    all_zips = sorted(set(users_by_zip) | set(jobs_by_zip) | set(resources_by_zip))
    for zip_code in all_zips:
        users = users_by_zip.get(zip_code, 0)
        jobs = jobs_by_zip.get(zip_code, 0)
        resources = resources_by_zip.get(zip_code, 0)
        score = ((jobs + resources) / users) if users else 0
        if score < 0.5:
            signal = "Gap"
            signal_key = "gap"
        elif score <= 1.0:
            signal = "Partial"
            signal_key = "partial"
        else:
            signal = "Covered"
            signal_key = "covered"

        zip_rows.append({
            "zip_area": zip_code,
            "users": users,
            "jobs": jobs,
            "resources": resources,
            "coverage_score": round(score, 2),
            "gap_signal": signal,
            "gap_signal_key": signal_key,
        })

    coverage_rows = sorted(
        [row for row in zip_rows if row["users"] > 0],
        key=lambda row: (-row["users"], row["coverage_score"], row["zip_area"]),
    )
    top_density = coverage_rows[:8]

    return {
        "users_by_zip": users_by_zip,
        "jobs_by_zip": jobs_by_zip,
        "resources_by_zip": resources_by_zip,
        "coverage_rows": coverage_rows,
        "top_density": top_density,
        "gap_count": sum(1 for row in coverage_rows if row["gap_signal_key"] == "gap"),
        "partial_count": sum(1 for row in coverage_rows if row["gap_signal_key"] == "partial"),
        "covered_count": sum(1 for row in coverage_rows if row["gap_signal_key"] == "covered"),
    }


def _analytics_context(active_tab):
    coverage = _coverage_dataset()
    users_by_zip = coverage["users_by_zip"]
    jobs_by_zip = coverage["jobs_by_zip"]
    resources_by_zip = coverage["resources_by_zip"]
    employers_by_zip = _zip_employer_counts()

    app_status_counts = {
        "submitted": Application.objects.filter(status="pending").count(),
        "under_review": Application.objects.filter(status="reviewed").count(),
        "interview": Application.objects.filter(status="interview").count(),
        "offered": Application.objects.filter(status="accepted").count(),
        "hired": 0,
        "rejected": Application.objects.filter(status="rejected").count(),
        "withdrawn": 0,
    }
    total_app_status = sum(app_status_counts.values()) or 1

    active_jobs = Job.objects.filter(is_active=True)
    fair_chance_jobs = active_jobs.count()
    total_jobs = Job.objects.count() or 1
    fair_chance_pct = round((fair_chance_jobs / total_jobs) * 100)

    approved_employers = EmployerProfile.objects.filter(verified=True).count()
    pending_employers = EmployerProfile.objects.filter(verified=False).count()
    total_users = User.objects.count()
    total_applications = Application.objects.count()
    active_orgs = ReentryOrganization.objects.count()

    tab_definitions = {
        "user-location": {
            "title": "User Location Intelligence",
            "subtitle": "Where users are - and how far they are from opportunity",
            "icon_key": "map",
        },
        "distribution": {
            "title": "Resource & Job Distribution Intelligence",
            "subtitle": "Where jobs and support exist - and where they do not",
            "icon_key": "distribution",
        },
        "match-quality": {
            "title": "Match Quality Metrics",
            "subtitle": "Proximity drives placement. This data proves it.",
            "icon_key": "target",
        },
        "growth-signals": {
            "title": "Platform Growth Signals",
            "subtitle": "Trends that show platform velocity and health",
            "icon_key": "growth",
        },
        "coverage-gaps": {
            "title": "Operational Coverage Gaps",
            "subtitle": "Coverage Score = (jobs + resources) / users per ZIP. Below 0.5 is a gap zone.",
            "icon_key": "alert",
        },
    }

    selected_tab = active_tab if active_tab in tab_definitions else "user-location"
    payload = tab_definitions[selected_tab]

    weekly_labels = ["W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9"]
    weekly_users = [0, 0, 0, 0, 0, 1, 0, 0]
    weekly_jobs = [0, 0, 0, 0, 0, 6, 0, 0]
    weekly_applications = [0, 0, 0, 0, 0, 5, 0, 0]
    weekly_max = 8

    svg_w = 920
    svg_h = 220
    pad_left = 34
    pad_right = 12
    pad_top = 12
    pad_bottom = 30
    plot_w = svg_w - pad_left - pad_right
    plot_h = svg_h - pad_top - pad_bottom
    step_x = plot_w / (max(len(weekly_labels) - 1, 1))

    def _point(index, value):
        x = pad_left + (index * step_x)
        y = pad_top + ((weekly_max - value) / weekly_max) * plot_h
        return x, y

    x_labels = []
    for idx, label in enumerate(weekly_labels):
        x, _ = _point(idx, 0)
        x_labels.append({"label": label, "x": round(x, 2)})

    y_ticks = []
    for tick in [0, 2, 4, 6, 8]:
        y = pad_top + ((weekly_max - tick) / weekly_max) * plot_h
        y_ticks.append({"value": tick, "y": round(y, 2)})

    def _polyline_points(series):
        points = []
        for idx, val in enumerate(series):
            x, y = _point(idx, val)
            points.append(f"{x:.2f},{y:.2f}")
        return " ".join(points)

    tab_data = {
        "user-location": {
            "kpi_cards": [
                {
                    "title": "AVG DISTANCE TO NEAREST JOB",
                    "value": "-",
                    "caption": "Across users with known ZIP",
                    "indicator": "green",
                },
                {
                    "title": "MEDIAN DISTANCE TO NEAREST JOB",
                    "value": "-",
                    "caption": "Across users with known ZIP",
                    "indicator": "blue",
                },
                {
                    "title": "USERS > 20 MI FROM ANY EMPLOYER",
                    "value": "0",
                    "caption": "Geographic gap signal",
                    "indicator": "orange",
                },
                {
                    "title": "USERS > 10 MI FROM ANY RESOURCE",
                    "value": "0",
                    "caption": "Reentry org coverage gap",
                    "indicator": "rose",
                },
            ],
            "chart_payloads": {
                "users_by_zip": {
                    "labels": list(users_by_zip.keys())[:8] or ["19132", "19133", "19134", "19139", "19140"],
                    "data": list(users_by_zip.values())[:8] or [14, 18, 11, 9, 7],
                    "max_value": max((list(users_by_zip.values())[:8] or [14, 18, 11, 9, 7]), default=1),
                },
            },
        },
        "distribution": {
            "kpi_cards": [
                {
                    "title": "ZIPS WITH ACTIVE JOBS",
                    "value": str(sum(1 for _, count in jobs_by_zip.items() if count > 0)),
                    "caption": "Employer geographic footprint",
                    "indicator": "green",
                },
                {
                    "title": "ZIPS WITH USER DEMAND BUT NO JOBS",
                    "value": str(sum(1 for zip_code, user_count in users_by_zip.items() if user_count > 0 and jobs_by_zip.get(zip_code, 0) == 0)),
                    "caption": "Employer recruitment targets",
                    "indicator": "orange",
                },
                {
                    "title": "FAIR-CHANCE COMPLIANT JOBS",
                    "value": f"{fair_chance_pct}%",
                    "caption": "of total",
                    "indicator": "blue",
                },
                {
                    "title": "ACTIVE REENTRY ORGS",
                    "value": str(active_orgs),
                    "caption": "Community support partners",
                    "indicator": "rose",
                },
            ],
            "chart_payloads": {
                "jobs_by_zip": {
                    "labels": list(jobs_by_zip.keys())[:8] or ["19132", "19133", "19134", "19139", "19140"],
                    "data": list(jobs_by_zip.values())[:8] or [12, 16, 8, 10, 5],
                    "max_value": max((list(jobs_by_zip.values())[:8] or [12, 16, 8, 10, 5]), default=1),
                },
                "employers_by_zip": {
                    "labels": list(employers_by_zip.keys())[:8] or ["19132", "19133", "19134", "19139", "19140"],
                    "data": list(employers_by_zip.values())[:8] or [6, 8, 4, 5, 3],
                    "max_value": max((list(employers_by_zip.values())[:8] or [6, 8, 4, 5, 3]), default=1),
                },
                "coverage_ranked": sorted(employers_by_zip.items(), key=lambda item: item[1], reverse=True)[:6]
                or [("19133", 8), ("19132", 6), ("19139", 5), ("19134", 4), ("19140", 3)],
                "coverage_rank_max": max(([count for _, count in sorted(employers_by_zip.items(), key=lambda item: item[1], reverse=True)[:6]] or [8, 6, 5, 4, 3]), default=1),
            },
        },
        "match-quality": {
            "kpi_cards": [
                {
                    "title": "FAIR-CHANCE JOB COVERAGE",
                    "value": f"{fair_chance_pct}%",
                    "caption": "of all listings",
                    "indicator": "green",
                },
                {
                    "title": "AVG JOBS PER ACTIVE ZIP",
                    "value": f"{round((sum(jobs_by_zip.values()) / (len(jobs_by_zip) or 1)), 1)}",
                    "caption": "Live listings per location",
                    "indicator": "blue",
                },
                {
                    "title": "TOTAL APPLICATIONS",
                    "value": str(total_applications),
                    "caption": "All time",
                    "indicator": "orange",
                },
                {
                    "title": "PLACEMENT (HIRED)",
                    "value": "0",
                    "caption": "0% hire rate",
                    "indicator": "rose",
                },
            ],
            "chart_payloads": {
                "ctr_by_distance": {
                    "labels": ["<5", "5-10", "10-20", "20-30", ">30"],
                    "data": [31, 24, 18, 10, 5],
                    "max_value": 31,
                },
                "apply_by_distance": {
                    "labels": ["<5", "5-10", "10-20", "20-30", ">30"],
                    "data": [19, 15, 11, 7, 3],
                    "max_value": 19,
                },
            },
            "status_breakdown": [
                {"label": "Submitted", "count": app_status_counts["submitted"], "percent": round((app_status_counts["submitted"] / total_app_status) * 100), "tone": "slate"},
                {"label": "Under Review", "count": app_status_counts["under_review"], "percent": round((app_status_counts["under_review"] / total_app_status) * 100), "tone": "blue"},
                {"label": "Interview", "count": app_status_counts["interview"], "percent": round((app_status_counts["interview"] / total_app_status) * 100), "tone": "indigo"},
                {"label": "Offered", "count": app_status_counts["offered"], "percent": round((app_status_counts["offered"] / total_app_status) * 100), "tone": "amber"},
                {"label": "Hired", "count": app_status_counts["hired"], "percent": round((app_status_counts["hired"] / total_app_status) * 100), "tone": "green"},
                {"label": "Rejected", "count": app_status_counts["rejected"], "percent": round((app_status_counts["rejected"] / total_app_status) * 100), "tone": "red"},
                {"label": "Withdrawn", "count": app_status_counts["withdrawn"], "percent": round((app_status_counts["withdrawn"] / total_app_status) * 100), "tone": "violet"},
            ],
        },
        "growth-signals": {
            "kpi_cards": [
                {
                    "title": "TOTAL USERS",
                    "value": str(total_users),
                    "caption": "Registered platform users",
                    "indicator": "green",
                },
                {
                    "title": "APPROVED EMPLOYERS",
                    "value": str(approved_employers),
                    "caption": f"{pending_employers} pending",
                    "indicator": "blue",
                },
                {
                    "title": "LIVE JOBS",
                    "value": str(active_jobs.count()),
                    "caption": "0 in queue",
                    "indicator": "orange",
                },
                {
                    "title": "EST. TIME-TO-HIRE",
                    "value": "18d",
                    "caption": "Avg days submitted to hired",
                    "indicator": "rose",
                },
            ],
            "chart_payloads": {
                "weekly_activity": {
                    "labels": weekly_labels,
                    "new_users": weekly_users,
                    "jobs_posted": weekly_jobs,
                    "applications": weekly_applications,
                    "max_value": weekly_max,
                    "svg": {
                        "width": svg_w,
                        "height": svg_h,
                        "plot_left": pad_left,
                        "plot_top": pad_top,
                        "plot_right": svg_w - pad_right,
                        "plot_bottom": svg_h - pad_bottom,
                        "plot_width": (svg_w - pad_right) - pad_left,
                        "plot_height": (svg_h - pad_bottom) - pad_top,
                        "x_labels": x_labels,
                        "y_ticks": y_ticks,
                        "users_points": _polyline_points(weekly_users),
                        "jobs_points": _polyline_points(weekly_jobs),
                        "applications_points": _polyline_points(weekly_applications),
                    },
                },
            },
            "approval_pipeline": [
                {"label": "Pending Review", "count": pending_employers, "tone": "amber"},
                {"label": "Approved", "count": approved_employers, "tone": "green"},
                {"label": "More Info Needed", "count": max(int(round(pending_employers * 0.25)), 0), "tone": "blue"},
                {"label": "Rejected", "count": max(int(round(pending_employers * 0.1)), 0), "tone": "red"},
            ],
            "hooks": {
                "directory_query_volume_by_zip": [],
                "radius_selection_patterns": [],
            },
        },
        "coverage-gaps": {
            "kpi_cards": [
                {
                    "title": "GAP ZIPS (SCORE < 0.5)",
                    "value": str(coverage["gap_count"]),
                    "caption": "Priority employer recruitment",
                    "indicator": "red",
                },
                {
                    "title": "PARTIAL COVERAGE ZIPS",
                    "value": str(coverage["partial_count"]),
                    "caption": "Score 0.5-1.0",
                    "indicator": "amber",
                },
                {
                    "title": "WELL-COVERED ZIPS",
                    "value": str(coverage["covered_count"]),
                    "caption": "Score >= 1.0",
                    "indicator": "green",
                },
            ],
            "chart_payloads": {
                "density_vs_supply": {
                    "rows": coverage["top_density"] or [
                        {"zip_area": "19132", "users": 18, "jobs": 8, "resources": 4},
                        {"zip_area": "19133", "users": 16, "jobs": 10, "resources": 5},
                        {"zip_area": "19134", "users": 14, "jobs": 7, "resources": 3},
                        {"zip_area": "19139", "users": 10, "jobs": 6, "resources": 2},
                    ],
                    "max_value": max(([row["users"] for row in coverage["top_density"]] or [18, 16, 14, 10]), default=1),
                },
            },
            "coverage_rows": coverage["coverage_rows"],
        },
    }

    density = tab_data["coverage-gaps"]["chart_payloads"]["density_vs_supply"]
    density_max = max(density.get("max_value") or 1, 1)
    segment_count = 20
    segment_range = list(range(segment_count))
    segmented_rows = []
    for row in density.get("rows", []):
        users_units = max(0, min(segment_count, round((row.get("users", 0) / density_max) * segment_count)))
        jobs_units = max(0, min(segment_count, round((row.get("jobs", 0) / density_max) * segment_count)))
        resources_units = max(0, min(segment_count, round((row.get("resources", 0) / density_max) * segment_count)))
        segmented_rows.append({
            **row,
            "segment_range": segment_range,
            "users_units": users_units,
            "jobs_units": jobs_units,
            "resources_units": resources_units,
        })
    density["segmented_rows"] = segmented_rows

    payload.update(tab_data[selected_tab])
    payload["active_tab"] = selected_tab
    payload["tab_items"] = [
        {"slug": "user-location", "label": "User Location", "icon_key": "map"},
        {"slug": "distribution", "label": "Distribution", "icon_key": "distribution"},
        {"slug": "match-quality", "label": "Match Quality", "icon_key": "target"},
        {"slug": "growth-signals", "label": "Growth Signals", "icon_key": "growth"},
        {"slug": "coverage-gaps", "label": "Coverage Gaps", "icon_key": "alert"},
    ]
    return payload


class AdminAnalyticsView(StaffRequiredMixin, View):
    template_name = "admin_portal/analytics/analytics.html"

    def get(self, request):
        active_tab = request.GET.get("tab") or "user-location"
        context = _analytics_context(active_tab)
        return render(request, self.template_name, context)


@login_required
@staff_member_required
def analytics_export(request):
    tab = request.GET.get("tab") or ""
    if tab != "coverage-gaps":
        return HttpResponseForbidden("Export is only available for coverage gaps.")

    dataset = _analytics_context("coverage-gaps")
    rows = dataset.get("coverage_rows", [])

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=coverage_gaps.csv"

    writer = csv.writer(response)
    writer.writerow(["ZIP / Area", "Users", "Jobs", "Resources", "Coverage Score", "Gap Signal"])
    for row in rows:
        writer.writerow([
            row["zip_area"],
            row["users"],
            row["jobs"],
            row["resources"],
            row["coverage_score"],
            row["gap_signal"],
        ])
    return response


class AdminDashboardView(StaffRequiredMixin, View):
    template_name = "admin_portal/dashboard.html"

    def get(self, request):
        seven_days_ago = timezone.now() - timedelta(days=7)

        active_users_7 = User.objects.filter(last_login__gte=seven_days_ago).count()
        jobs_pending_review = Job.objects.filter(is_flagged=True).count()
        employers_pending = EmployerProfile.objects.filter(verified=False).count()
        open_flags = jobs_pending_review
        site_views_7 = 0

        review_queue = []
        for job in Job.objects.filter(is_flagged=True).order_by("-created_at")[:6]:
            review_queue.append({
                "title": job.title,
                "reason": job.flagged_reason or "Job listing flagged for review",
                "timestamp": job.created_at,
                "severity": "high",
                "url": reverse("admin_portal:job_detail", args=[job.id]),
            })

        for employer in EmployerProfile.objects.filter(verified=False).select_related("user").order_by("-user__date_joined")[:6]:
            review_queue.append({
                "title": employer.company_name,
                "reason": "Pending employer approval",
                "timestamp": employer.user.date_joined,
                "severity": "medium",
                "url": reverse("admin_portal:employer_detail", args=[employer.id]),
            })

        review_queue = sorted(review_queue, key=lambda item: item["timestamp"] or timezone.now(), reverse=True)[:8]

        activity_items = []
        for app in Application.objects.select_related("job", "applicant").order_by("-submitted_at")[:6]:
            activity_items.append({
                "title": f"{app.applicant.get_full_name() or app.applicant.username} applied",
                "detail": app.job.title,
                "timestamp": app.submitted_at,
            })
        for job in Job.objects.select_related("employer").order_by("-created_at")[:4]:
            activity_items.append({
                "title": job.title,
                "detail": f"Posted by {job.employer.get_full_name() or job.employer.username}",
                "timestamp": job.created_at,
            })
        activity_items = sorted(activity_items, key=lambda item: item["timestamp"] or timezone.now(), reverse=True)[:8]

        context = {
            "active_users_7": active_users_7,
            "jobs_pending_review": jobs_pending_review,
            "employers_pending": employers_pending,
            "open_flags": open_flags,
            "site_views_7": site_views_7,
            "review_queue": review_queue,
            "activity_items": activity_items,
        }
        return render(request, self.template_name, context)


class ApplicationListView(StaffRequiredMixin, ListView):
    model = Application
    template_name = "admin_portal/applications_list.html"
    context_object_name = "applications"
    paginate_by = 20

    def get_queryset(self):
        qs = Application.objects.select_related("job", "applicant").all().order_by("-submitted_at")
        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip().lower()
        if q:
            qs = qs.filter(
                Q(job__title__icontains=q)
                | Q(applicant__username__icontains=q)
                | Q(applicant__email__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        sort = self.request.GET.get("sort")
        if sort in {"submitted_at", "status"}:
            qs = qs.order_by(sort)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["status"] = self.request.GET.get("status", "")
        context["sort"] = self.request.GET.get("sort", "")
        try:
            context["status_choices"] = Application._meta.get_field("status").choices
        except Exception:
            context["status_choices"] = Application.STATUS_CHOICES
        return context


class AuditLogListView(StaffRequiredMixin, ListView):
    model = AuditLog
    template_name = "admin_portal/audit_log.html"
    context_object_name = "logs"
    paginate_by = 30

    def get_queryset(self):
        qs = AuditLog.objects.select_related("actor").all()
        q = (self.request.GET.get("q") or "").strip()
        action = (self.request.GET.get("action") or "").strip().lower()
        if q:
            qs = qs.filter(
                Q(object_type__icontains=q)
                | Q(object_repr__icontains=q)
                | Q(actor__username__icontains=q)
            )
        if action:
            qs = qs.filter(action=action)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["action"] = self.request.GET.get("action", "")
        summary = AuditLog.objects.values("action").annotate(count=Count("id"))
        context["action_summary"] = {row["action"]: row["count"] for row in summary}
        return context


@login_required
@staff_member_required
def audit_log_export(request):
    logs = AuditLog.objects.select_related("actor").order_by("-created_at")
    q = (request.GET.get("q") or "").strip()
    action = (request.GET.get("action") or "").strip().lower()
    if q:
        logs = logs.filter(
            Q(object_type__icontains=q)
            | Q(object_repr__icontains=q)
            | Q(actor__username__icontains=q)
        )
    if action:
        logs = logs.filter(action=action)
    rows = [
        ["date", "admin", "action", "target_type", "target", "details"],
    ]
    for log in logs[:5000]:
        rows.append([
            log.created_at.isoformat(),
            log.actor.get_username() if log.actor else "",
            log.action,
            log.object_type,
            log.object_repr,
            (log.metadata.get("note") or log.metadata.get("reason") or ""),
        ])
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=audit_log.csv"
    writer = csv.writer(response)
    writer.writerows(rows)
    return response


class ModuleListView(StaffRequiredMixin, ListView):
    model = Module
    template_name = "admin_portal/content_list.html"
    context_object_name = "modules"
    paginate_by = 20

    def get_queryset(self):
        qs = Module.objects.all().order_by("-created_at")
        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip().lower()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if status == "archived":
            qs = qs.filter(is_archived=True)
        else:
            qs = qs.filter(is_archived=False)
        if status in {"published", "draft"}:
            filtered = []
            for item in qs:
                is_published = bool(item.video_url or item.embed_html or item.internal_content)
                if status == "published" and is_published:
                    filtered.append(item.id)
                if status == "draft" and not is_published:
                    filtered.append(item.id)
            qs = qs.filter(id__in=filtered)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["status"] = self.request.GET.get("status", "")
        return context


class ModuleCreateView(StaffRequiredMixin, CreateView):
    model = Module
    form_class = ModuleForm
    template_name = "admin_portal/content_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        _log_action(self.request.user, "create", self.object)
        return response

    def get_success_url(self):
        return reverse("admin_portal:content_list")


class ModuleUpdateView(StaffRequiredMixin, UpdateView):
    model = Module
    form_class = ModuleForm
    template_name = "admin_portal/content_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        _log_action(self.request.user, "update", self.object)
        return response

    def get_success_url(self):
        return reverse("admin_portal:content_list")


class ModuleDetailView(StaffRequiredMixin, DetailView):
    model = Module
    template_name = "admin_portal/content_detail.html"
    context_object_name = "module"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["audit_logs"] = AuditLog.objects.filter(
            object_type="Module", object_id=str(self.object.id)
        )[:20]
        return context


class ModuleDeleteView(StaffRequiredMixin, DeleteView):
    model = Module
    template_name = "admin_portal/content_confirm_delete.html"
    success_url = reverse_lazy("admin_portal:content_list")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        _log_action(request.user, "delete", obj)
        messages.success(request, "Module deleted.")
        return super().delete(request, *args, **kwargs)


@login_required
@staff_member_required
def module_archive(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    module = get_object_or_404(Module, pk=pk)
    module.is_archived = True
    module.save(update_fields=["is_archived"])
    _log_action(request.user, "update", module, {"is_archived": True})
    messages.success(request, "Module archived.")
    return redirect("admin_portal:content_detail", pk=module.id)


class UserListView(StaffRequiredMixin, ListView):
    model = User
    template_name = "admin_portal/users_list.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.all().order_by("-date_joined")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(email__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
            )
        role = (self.request.GET.get("role") or "").strip().lower()
        if role == "admin":
            qs = qs.filter(is_staff=True)
        elif role == "employer":
            qs = qs.filter(groups__name__in=["Employer", "Employers"]).distinct()
        elif role == "seeker":
            qs = qs.exclude(groups__name__in=["Employer", "Employers"]).filter(is_staff=False)
        status = (self.request.GET.get("status") or "").strip().lower()
        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "suspended":
            qs = qs.filter(is_active=False)
        sort = self.request.GET.get("sort")
        if sort in {"date_joined", "last_login", "username"}:
            qs = qs.order_by(sort)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["sort"] = self.request.GET.get("sort", "")
        context["role"] = self.request.GET.get("role", "")
        context["status"] = self.request.GET.get("status", "")
        return context


class UserDetailView(StaffRequiredMixin, DetailView):
    model = User
    template_name = "admin_portal/users_detail.html"
    context_object_name = "target_user"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["note_form"] = UserNoteForm()
        context["audit_logs"] = AuditLog.objects.filter(
            object_type="User", object_id=str(self.object.id)
        )[:20]
        return context


@login_required
@staff_member_required
def user_toggle_active(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    user = get_object_or_404(User, pk=pk)
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    _log_action(request.user, "update", user, {"is_active": user.is_active})
    messages.success(request, "User status updated.")
    return redirect("admin_portal:user_detail", pk=user.id)


@login_required
@staff_member_required
def user_add_note(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    user = get_object_or_404(User, pk=pk)
    form = UserNoteForm(request.POST)
    if form.is_valid():
        _log_action(request.user, "note", user, {"note": form.cleaned_data["note"]})
        messages.success(request, "Note saved.")
    return redirect("admin_portal:user_detail", pk=user.id)


class EmployerListView(StaffRequiredMixin, ListView):
    model = EmployerProfile
    template_name = "admin_portal/employers_list.html"
    context_object_name = "employers"
    paginate_by = 20

    def get_queryset(self):
        qs = EmployerProfile.objects.select_related("user").all().order_by("-user__date_joined")
        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip().lower()
        if q:
            qs = qs.filter(
                Q(company_name__icontains=q)
                | Q(user__email__icontains=q)
                | Q(user__username__icontains=q)
            )
        if status == "approved":
            qs = qs.filter(verified=True)
        elif status == "pending":
            qs = qs.filter(verified=False)
        sort = self.request.GET.get("sort")
        if sort in {"company_name", "user__date_joined"}:
            qs = qs.order_by(sort)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["status"] = self.request.GET.get("status", "")
        context["sort"] = self.request.GET.get("sort", "")
        return context


class EmployerDetailView(StaffRequiredMixin, DetailView):
    model = EmployerProfile
    template_name = "admin_portal/employers_detail.html"
    context_object_name = "employer"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["notes_form"] = EmployerNotesForm(instance=self.object)
        context["audit_logs"] = AuditLog.objects.filter(
            object_type="EmployerProfile", object_id=str(self.object.id)
        )[:20]
        return context


class EmployerUpdateView(StaffRequiredMixin, UpdateView):
    model = EmployerProfile
    form_class = EmployerProfileForm
    template_name = "admin_portal/employers_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        _log_action(self.request.user, "update", self.object)
        return response

    def get_success_url(self):
        return reverse("admin_portal:employer_detail", args=[self.object.id])


@login_required
@staff_member_required
def employer_update_notes(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    employer = get_object_or_404(EmployerProfile, pk=pk)
    form = EmployerNotesForm(request.POST, instance=employer)
    if form.is_valid():
        form.save()
        _log_action(request.user, "note", employer, {"note": form.cleaned_data["verification_notes"]})
        messages.success(request, "Notes updated.")
    return redirect("admin_portal:employer_detail", pk=pk)


@login_required
@staff_member_required
def employer_approve(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    employer = get_object_or_404(EmployerProfile, pk=pk)
    employer.verified = True
    employer.verified_at = timezone.now()
    employer.save(update_fields=["verified", "verified_at"])
    _log_action(request.user, "approve", employer)
    messages.success(request, "Employer approved.")
    return redirect("admin_portal:employer_detail", pk=pk)


@login_required
@staff_member_required
def employer_reject(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    employer = get_object_or_404(EmployerProfile, pk=pk)
    employer.verified = False
    employer.save(update_fields=["verified"])
    _log_action(request.user, "reject", employer)
    messages.success(request, "Employer marked as unverified.")
    return redirect("admin_portal:employer_detail", pk=pk)


class JobListView(StaffRequiredMixin, ListView):
    model = Job
    template_name = "admin_portal/jobs_list.html"
    context_object_name = "jobs"
    paginate_by = 20

    def get_queryset(self):
        qs = Job.objects.select_related("employer").all().order_by("-created_at")
        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip().lower()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(employer__username__icontains=q)
                | Q(location__icontains=q)
            )
        if status == "active":
            qs = qs.filter(is_active=True, is_flagged=False)
        elif status == "inactive":
            qs = qs.filter(is_active=False)
        elif status == "flagged":
            qs = qs.filter(is_flagged=True)
        sort = self.request.GET.get("sort")
        if sort in {"created_at", "title"}:
            qs = qs.order_by(sort)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["status"] = self.request.GET.get("status", "")
        context["sort"] = self.request.GET.get("sort", "")
        return context


class JobDetailView(StaffRequiredMixin, DetailView):
    model = Job
    template_name = "admin_portal/jobs_detail.html"
    context_object_name = "job"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["review_form"] = JobReviewForm(instance=self.object)
        context["audit_logs"] = AuditLog.objects.filter(
            object_type="Job", object_id=str(self.object.id)
        )[:20]
        return context


class JobUpdateView(StaffRequiredMixin, UpdateView):
    model = Job
    form_class = JobForm
    template_name = "admin_portal/jobs_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        _log_action(self.request.user, "update", self.object)
        return response

    def get_success_url(self):
        return reverse("admin_portal:job_detail", args=[self.object.id])


@login_required
@staff_member_required
def job_approve(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    job = get_object_or_404(Job, pk=pk)
    job.is_active = True
    job.is_flagged = False
    job.flagged_reason = ""
    job.save(update_fields=["is_active", "is_flagged", "flagged_reason"])
    _log_action(request.user, "approve", job)
    messages.success(request, "Job approved.")
    return redirect("admin_portal:job_detail", pk=pk)


@login_required
@staff_member_required
def job_reject(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    job = get_object_or_404(Job, pk=pk)
    form = JobReviewForm(request.POST, instance=job)
    if form.is_valid():
        job = form.save(commit=False)
    job.is_active = False
    job.is_flagged = True
    job.save(update_fields=["is_active", "is_flagged", "flagged_reason"])
    _log_action(request.user, "reject", job, {"reason": job.flagged_reason})
    messages.success(request, "Job rejected and flagged.")
    return redirect("admin_portal:job_detail", pk=pk)


class OrganizationListView(StaffRequiredMixin, ListView):
    model = ReentryOrganization
    template_name = "admin_portal/orgs_list.html"
    context_object_name = "orgs"
    paginate_by = 20

    def get_queryset(self):
        qs = ReentryOrganization.objects.all().order_by("name")
        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip().lower()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q) | Q(state__icontains=q))
        if status == "verified":
            qs = qs.filter(is_verified=True)
        elif status == "pending":
            qs = qs.filter(is_verified=False)
        sort = self.request.GET.get("sort")
        if sort in {"name", "created_at"}:
            qs = qs.order_by(sort)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["status"] = self.request.GET.get("status", "")
        context["sort"] = self.request.GET.get("sort", "")
        return context


class OrganizationDetailView(StaffRequiredMixin, DetailView):
    model = ReentryOrganization
    template_name = "admin_portal/orgs_detail.html"
    context_object_name = "org"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["audit_logs"] = AuditLog.objects.filter(
            object_type="ReentryOrganization", object_id=str(self.object.id)
        )[:20]
        return context


class OrganizationCreateView(StaffRequiredMixin, CreateView):
    model = ReentryOrganization
    form_class = ReentryOrganizationForm
    template_name = "admin_portal/orgs_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        _log_action(self.request.user, "create", self.object)
        return response

    def get_success_url(self):
        return reverse("admin_portal:org_detail", args=[self.object.id])


class OrganizationUpdateView(StaffRequiredMixin, UpdateView):
    model = ReentryOrganization
    form_class = ReentryOrganizationForm
    template_name = "admin_portal/orgs_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        _log_action(self.request.user, "update", self.object)
        return response

    def get_success_url(self):
        return reverse("admin_portal:org_detail", args=[self.object.id])


class OrganizationDeleteView(StaffRequiredMixin, DeleteView):
    model = ReentryOrganization
    template_name = "admin_portal/orgs_confirm_delete.html"
    success_url = reverse_lazy("admin_portal:org_list")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        _log_action(request.user, "delete", obj)
        messages.success(request, "Organization deleted.")
        return super().delete(request, *args, **kwargs)
