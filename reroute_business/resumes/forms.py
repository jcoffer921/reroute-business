# resumes/forms.py
"""
Resume builder forms. Adds light validation and consistent CSS hooks.
"""

from django import forms
from django.forms import modelformset_factory, BaseModelFormSet
from django.core.exceptions import ValidationError

from .models import Resume, ContactInfo, Education, Experience, Project
from core.models import Skill

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
        phone = (self.cleaned_data.get('phone') or '').strip()
        if phone and len(phone) < 7:
            raise ValidationError("Please enter a valid phone number.")
        return phone

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make city/state required at the form layer even though model allows blank
        self.fields['city'].required = True
        self.fields['state'].required = True

    def clean(self):
        cleaned = super().clean()
        city = (cleaned.get('city') or '').strip()
        state = (cleaned.get('state') or '').strip()
        if not city:
            self.add_error('city', 'City is required.')
        if not state:
            self.add_error('state', 'State is required.')
        return cleaned


# ---------- Step 2: Education ----------

class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ['school', 'degree', 'start_date', 'end_date', 'description']
        widgets = {
            'school': forms.TextInput(attrs={'class': 'form-control school-input'}),
            'degree': forms.TextInput(attrs={'class': 'form-control degree-input'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control start-input'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control end-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control description-input', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # These are optional in your flow
        self.fields['degree'].required = False
        self.fields['end_date'].required = False
        self.fields['description'].required = False

    def clean(self):
        """
        Ensure end_date is not before start_date (when both provided).
        This prevents awkward timeline issues in the preview.
        """
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        if start and end and end < start:
            self.add_error('end_date', "End date cannot be before start date.")
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
    formset=RequiredOneFormSet,
    extra=1,           # Keep at least one blank row
    can_delete=True
)


# ---------- Step 3: Experience ----------

class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = ['job_title', 'company', 'start_date', 'end_date', 'currently_work_here', 'description']
        widgets = {
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'currently_work_here': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'e.g. Promoted for leadership, Managed floor staff, Handled ticket sales...'
            }),
        }

    def clean(self):
        """
        If 'currently_work_here' is checked, allow blank end_date.
        Otherwise, validate chronology.
        """
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        current = cleaned.get('currently_work_here')

        if not current and start and end and end < start:
            self.add_error('end_date', "End date cannot be before start date.")
        return cleaned


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
