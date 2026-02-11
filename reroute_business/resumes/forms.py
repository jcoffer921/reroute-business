# resumes/forms.py
"""
Resume builder forms. Adds light validation and consistent CSS hooks.
"""

from django import forms
from django.forms import modelformset_factory, BaseModelFormSet
from django.core.exceptions import ValidationError

from .models import Resume, ContactInfo, Education, Experience, Project, EducationType
from reroute_business.core.models import Skill

# ---------- Step 1: Contact Info ----------

class ContactInfoForm(forms.ModelForm):
    class Meta:
        model = ContactInfo
        fields = ['full_name', 'email', 'phone', 'city', 'state']
        widgets = {
            'full_name': forms.TextInput(attrs={'id': 'id_full_name', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'id': 'id_email', 'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'id': 'id_phone', 'class': 'form-control'}),
            'city': forms.TextInput(attrs={'id': 'id_city', 'class': 'form-control'}),
            'state': forms.Select(attrs={'id': 'id_state', 'class': 'form-control'}),
        }

    # Optional: basic phone normalization (very light)
    def clean_phone(self):
        raw = (self.cleaned_data.get('phone') or '').strip()
        phone = "".join(ch for ch in raw if ch.isdigit())
        if not phone:
            raise ValidationError("Phone number is required.")
        if len(phone) < 7:
            raise ValidationError("Please enter a valid phone number.")
        return phone

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # City/state are optional in the resume flow
        self.fields['city'].required = False
        self.fields['state'].required = False

    def clean(self):
        cleaned = super().clean()
        return cleaned


# ---------- Step 2: Education ----------

class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ['education_type', 'school', 'field_of_study', 'year', 'details']
        widgets = {
            'education_type': forms.Select(attrs={'class': 'form-control'}),
            'school': forms.TextInput(attrs={'class': 'form-control'}),
            'field_of_study': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'maxlength': '4'}),
            'details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['education_type'].queryset = EducationType.objects.all()
        self.fields['education_type'].required = False
        self.fields['school'].required = False
        self.fields['field_of_study'].required = False
        self.fields['year'].required = False
        self.fields['details'].required = False

    def clean_year(self):
        year = (self.cleaned_data.get('year') or '').strip()
        if year and (not year.isdigit() or len(year) != 4):
            raise ValidationError("Enter a 4-digit year.")
        return year

    def clean(self):
        cleaned = super().clean()
        edu_type = cleaned.get("education_type")
        has_any = any(
            (cleaned.get("school") or "").strip() or
            (cleaned.get("field_of_study") or "").strip() or
            (cleaned.get("year") or "").strip() or
            (cleaned.get("details") or "").strip()
        )
        if has_any and not edu_type:
            self.add_error("education_type", "Select a type.")
        return cleaned


class RequiredOneFormSet(BaseModelFormSet):
    """Require at least one non-deleted, non-empty form."""
    def clean(self):
        super().clean()
        valid_count = 0
        for form in self.forms:
            cd = getattr(form, 'cleaned_data', None)
            if not cd:
                continue
            if cd.get('DELETE'):
                continue
            # consider a form non-empty if any field (excluding DELETE) has a value
            has_any = any(v not in (None, '', []) for k, v in cd.items() if k != 'DELETE')
            if has_any:
                valid_count += 1
        if valid_count == 0:
            raise ValidationError('Add at least one entry before continuing.')


EducationFormSet = modelformset_factory(
    Education,
    form=EducationForm,
    extra=1,           # Keep at least one blank row
    can_delete=True
)


# ---------- Step 3: Experience ----------

class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = ['role_type', 'job_title', 'company', 'start_year', 'end_year', 'currently_work_here', 'responsibilities', 'tools']
        widgets = {
            'role_type': forms.Select(attrs={'class': 'form-control'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.TextInput(attrs={'class': 'form-control'}),
            'start_year': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'maxlength': '4'}),
            'end_year': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'maxlength': '4'}),
            'currently_work_here': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'responsibilities': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Add one responsibility per line...'
            }),
            'tools': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean(self):
        """
        If 'currently_work_here' is checked, allow blank end_year.
        """
        cleaned = super().clean()
        start = (cleaned.get('start_year') or '').strip()
        end = (cleaned.get('end_year') or '').strip()
        current = cleaned.get('currently_work_here')

        if start and (not start.isdigit() or len(start) != 4):
            self.add_error('start_year', "Enter a 4-digit year.")
        if end and (not end.isdigit() or len(end) != 4):
            self.add_error('end_year', "Enter a 4-digit year.")
        if not current and start and end and start.isdigit() and end.isdigit() and int(end) < int(start):
            self.add_error('end_year', "End year cannot be before start year.")
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsibilities'].required = True
        self.fields['tools'].required = False


ExperienceFormSet = modelformset_factory(
    Experience,
    form=ExperienceForm,
    formset=RequiredOneFormSet,
    extra=1,
    can_delete=True
)


# ---------- Step 4: Skills ----------

class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Add a skill and press Enter'})
        }


# ---------- Step 5: Projects (Optional) ----------

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'link', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ---------- Resume Import ----------

class ResumeImportForm(forms.Form):
    """
    Simple wrapper for the upload control on the import page.
    We still perform server-side validation in the parser functions.
    """
    resume_file = forms.FileField(label='Upload Resume', required=True)
