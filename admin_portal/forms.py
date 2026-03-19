from django import forms
from reroute_business.job_list.models import Job
from reroute_business.profiles.models import EmployerProfile
from reroute_business.resources.models import Module, ResourceOrganization


class UserNoteForm(forms.Form):
    note = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "class": "admin-textarea"}),
        label="Internal note",
    )


class EmployerNotesForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ["verification_notes"]
        widgets = {
            "verification_notes": forms.Textarea(attrs={"rows": 3, "class": "admin-textarea"}),
        }


class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = [
            "company_name",
            "website",
            "description",
            "verified",
            "verification_notes",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "class": "admin-textarea"}),
            "verification_notes": forms.Textarea(attrs={"rows": 3, "class": "admin-textarea"}),
        }


class JobReviewForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ["flagged_reason"]
        widgets = {
            "flagged_reason": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Reason for rejection", "class": "admin-textarea"}
            ),
        }


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            "title",
            "description",
            "requirements",
            "location",
            "zip_code",
            "job_type",
            "experience_level",
            "salary_type",
            "salary_min",
            "salary_max",
            "hourly_min",
            "hourly_max",
            "is_active",
            "is_flagged",
            "flagged_reason",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "class": "admin-textarea"}),
            "requirements": forms.Textarea(attrs={"rows": 3, "class": "admin-textarea"}),
            "flagged_reason": forms.Textarea(attrs={"rows": 3, "class": "admin-textarea"}),
        }


class ResourceOrganizationForm(forms.ModelForm):
    class Meta:
        model = ResourceOrganization
        fields = [
            "name",
            "category",
            "is_verified",
            "is_active",
            "website",
            "overview",
            "address_line",
            "neighborhood",
            "zip_code",
            "phone",
        ]
        widgets = {
            "overview": forms.Textarea(attrs={"rows": 4, "class": "admin-textarea"}),
        }


class ModuleForm(forms.ModelForm):
    key_takeaways = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "admin-textarea"}),
        help_text="One takeaway per line.",
    )

    class Meta:
        model = Module
        fields = [
            "title",
            "description",
            "category",
            "gallery_category",
            "duration_minutes",
            "quiz_lesson_count",
            "key_takeaways",
            "video_url",
            "embed_html",
            "internal_content",
            "poster_image",
            "is_archived",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "class": "admin-textarea"}),
            "embed_html": forms.Textarea(attrs={"rows": 4, "class": "admin-textarea"}),
            "internal_content": forms.Textarea(attrs={"rows": 4, "class": "admin-textarea"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        takeaways = getattr(self.instance, "key_takeaways", None)
        if takeaways:
            self.initial["key_takeaways"] = "\n".join(str(item).strip() for item in takeaways if str(item).strip())

    def clean_key_takeaways(self):
        raw = (self.cleaned_data.get("key_takeaways") or "").splitlines()
        return [line.strip() for line in raw if line.strip()]
