from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from datetime import timedelta

from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.contrib import messages

from reroute_business.job_list.models import Job, Application
from reroute_business.profiles.models import EmployerProfile
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
