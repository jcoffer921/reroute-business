# forms.py
# ─────────────────────────────────────────────────────────────────────────────
# Purpose:
# - Provide a clean signup form that renders styled inputs without template hacks
# - Enforce password rules and confirmation
# - Hash the password before saving
# - Keep profile + step forms simple and readable
# ─────────────────────────────────────────────────────────────────────────────

import re
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from reroute_business.profiles.models import UserProfile
from django.contrib.auth.forms import PasswordChangeForm
from reroute_business.profiles.constants import USER_STATUS_CHOICES
from reroute_business.main.models import AgencyPartnershipApplication


class UserSignupForm(forms.ModelForm):
    """
    Signup form with explicit widgets (so templates can simply do {{ user_form.field }}).
    We also add a confirm_password field that's validated in clean().
    """

    # --- Top-of-form identity fields (with usability-friendly attributes) ---
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "First name",
            "autocomplete": "given-name",
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Last name",
            "autocomplete": "family-name",
        })
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Your username",
            "autocomplete": "username",
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            "class": "input",
            "placeholder": "you@example.com",
            "autocomplete": "email",
        })
    )

    # --- Passwords (Django will clear these on error by design) -------------
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "input",
            "placeholder": "Create a password",
            "autocomplete": "new-password",
        })
    )
    confirm_password = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={
            "class": "input",
            "placeholder": "Confirm password",
            "autocomplete": "new-password",
        })
    )

    class Meta:
        model = User
        # NOTE: confirm_password is not in the model, so it's not listed here.
        fields = ["first_name", "last_name", "username", "email", "password"]

    # ------------------------- Validators -----------------------------------
    def clean_email(self):
        """
        Enforce unique emails (case-insensitive) so users can't sign up twice.
        """
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with that email already exists.")
        return email

    def clean_password(self):
        """
        Keep your existing password policy for transparency and consistency.
        """
        password = self.cleaned_data.get("password")
        if not password:
            raise ValidationError("Password is required.")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        if not re.search(r"\d", password):
            raise ValidationError("Password must include at least one number.")
        if not re.search(r"[A-Z]", password):
            raise ValidationError("Password must include at least one uppercase letter.")
        if not re.search(r"[a-z]", password):
            raise ValidationError("Password must include at least one lowercase letter.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise ValidationError("Password must include at least one special character.")
        return password

    def clean(self):
        """
        Cross-field validation to ensure passwords match.
        """
        cleaned = super().clean()
        pwd = cleaned.get("password")
        confirm = cleaned.get("confirm_password")
        if pwd and confirm and pwd != confirm:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        """
        Hash the password and save the user.
        """
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])  # Hashes password
        if commit:
            user.save()
        return user


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Small UX touch: placeholders on password change fields.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].widget.attrs.update({
            "class": "input",
            "placeholder": "Current Password"
        })
        self.fields["new_password1"].widget.attrs.update({
            "class": "input",
            "placeholder": "New Password"
        })
        self.fields["new_password2"].widget.attrs.update({
            "class": "input",
            "placeholder": "Confirm Password"
        })


class UserProfileForm(forms.ModelForm):
    """
    Minimal profile edit form; widgets keep styling consistent without template hacks.
    """
    class Meta:
        model = UserProfile
        fields = ["bio", "profile_picture"]
        widgets = {
            "bio": forms.Textarea(attrs={
                "class": "textarea",
                "rows": 4,
                "placeholder": "Tell us a bit about yourself"
            }),
        }


# ================= Account Preferences =================
class AccountPreferencesForm(forms.Form):
    """
    Settings: username (system id), display name, and employment status.
    - Username must be unique (case-insensitive) aside from the current user
    - Display name maps to UserProfile.preferred_name
    - Status maps to UserProfile.status (choices from USER_STATUS_CHOICES)
    """
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "input-small",
            "placeholder": "Username",
            "autocomplete": "username",
        })
    )
    display_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "input-small",
            "placeholder": "Display Name (public-facing)",
        })
    )
    status = forms.ChoiceField(
        choices=USER_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            "class": "input-small",
        })
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise ValidationError("Username is required.")
        # Enforce uniqueness ignoring the current user
        qs = User.objects.filter(username__iexact=username)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise ValidationError("That username is taken. Please choose another.")
        return username


class RecoveryOptionsForm(forms.Form):
    """
    Sign In & Security: Recovery options for account access.
    Maps to UserProfile.personal_email and UserProfile.phone_number.
    """
    backup_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            "class": "input-small",
            "placeholder": "Backup email (optional)",
            "autocomplete": "email",
        })
    )
    backup_phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            "class": "input-small",
            "placeholder": "Backup phone (optional)",
            "autocomplete": "tel",
        })
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

# -------------------------- Onboarding Step Forms ---------------------------
# These can remain plain, but we add attributes to keep styling consistent.

class Step1Form(forms.Form):
    full_name = forms.CharField(
        label="Full Name",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "Full name"})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "input", "placeholder": "you@example.com"})
    )


class Step2Form(forms.Form):
    bio = forms.CharField(
        widget=forms.Textarea(attrs={"class": "textarea", "rows": 4, "placeholder": "Short bio"}),
        required=False
    )
    profile_picture = forms.ImageField(required=False)


class Step3Form(forms.Form):
    emergency_contact = forms.CharField(
        label="Emergency Contact",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "input"})
    )
    relationship = forms.CharField(
        label="Relationship to Emergency Contact",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "input"})
    )


class Step4Form(forms.Form):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "class": "input"})
    )
    race = forms.ChoiceField(
        choices=[
            ("Black", "Black or African American"),
            ("White", "White"),
            ("Asian", "Asian"),
            ("Latino", "Latino or Hispanic"),
            ("Native", "Native American"),
            ("Other", "Other"),
        ],
        widget=forms.Select(attrs={"class": "input"})
    )


class AgencyPartnershipApplicationForm(forms.ModelForm):
    SERVICE_CHOICES = [
        ("workforce_development", "Workforce Development"),
        ("job_placement", "Job Placement"),
        ("resume_assistance", "Resume Assistance"),
        ("ged_education", "GED / Education"),
        ("mental_health_support", "Mental Health Support"),
        ("housing_assistance", "Housing Assistance"),
        ("legal_services", "Legal Services"),
        ("id_assistance", "ID Assistance"),
        ("benefits_navigation", "Benefits Navigation"),
        ("mentorship", "Mentorship"),
        ("other", "Other"),
    ]

    TARGET_POPULATION_CHOICES = [
        ("youth", "Youth"),
        ("veterans", "Veterans"),
        ("returning_citizens", "Returning citizens"),
        ("general_workforce", "General workforce"),
    ]

    BOOLEAN_CHOICES = [
        (True, "Yes"),
        (False, "No"),
    ]

    services_offered = forms.MultipleChoiceField(
        choices=SERVICE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    target_population = forms.MultipleChoiceField(
        choices=TARGET_POPULATION_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    supports_justice_impacted = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput,
    )
    supports_recently_released = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput,
    )
    requires_government_id = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput,
    )
    requires_release_window = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput,
    )
    requires_orientation_attendance = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput,
    )
    requires_intake_assessment = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput,
    )
    requires_service_area_residency = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput,
    )
    referral_method_preference = forms.ChoiceField(
        choices=AgencyPartnershipApplication.REFERRAL_METHOD_CHOICES,
        required=False,
        widget=forms.RadioSelect,
    )
    tracks_employment_outcomes = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput,
    )
    open_to_referral_tracking = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput,
    )
    interested_in_featured_verified = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput,
    )

    class Meta:
        model = AgencyPartnershipApplication
        fields = [
            "organization_name",
            "primary_contact_name",
            "contact_email",
            "contact_phone",
            "website",
            "physical_address",
            "service_area",
            "year_founded",
            "organization_type",
            "services_offered",
            "services_other",
            "target_population",
            "target_population_other",
            "supports_justice_impacted",
            "supports_recently_released",
            "requires_government_id",
            "requires_release_window",
            "requires_orientation_attendance",
            "requires_intake_assessment",
            "requires_service_area_residency",
            "additional_eligibility_details",
            "average_served_per_month",
            "intake_process_description",
            "referral_method_preference",
            "tracks_employment_outcomes",
            "open_to_referral_tracking",
            "partnership_reason",
            "reroute_support_needs",
            "interested_in_featured_verified",
            "accuracy_confirmation",
            "terms_privacy_agreement",
            "logo",
        ]
        widgets = {
            "organization_name": forms.TextInput(attrs={"class": "input", "placeholder": "Organization name"}),
            "primary_contact_name": forms.TextInput(attrs={"class": "input", "placeholder": "Primary contact name"}),
            "contact_email": forms.EmailInput(attrs={"class": "input", "placeholder": "name@organization.org"}),
            "contact_phone": forms.TextInput(attrs={"class": "input", "placeholder": "(555) 555-5555"}),
            "website": forms.URLInput(attrs={"class": "input", "placeholder": "https://"}),
            "physical_address": forms.TextInput(attrs={"class": "input", "placeholder": "Street, City, State"}),
            "service_area": forms.TextInput(attrs={"class": "input", "placeholder": "City / ZIP coverage"}),
            "year_founded": forms.NumberInput(attrs={"class": "input", "placeholder": "YYYY", "min": "1800", "max": "2100"}),
            "organization_type": forms.Select(attrs={"class": "input"}),
            "services_other": forms.TextInput(attrs={"class": "input", "placeholder": "Other service (if applicable)"}),
            "target_population_other": forms.TextInput(attrs={"class": "input", "placeholder": "Other population (if applicable)"}),
            "additional_eligibility_details": forms.Textarea(attrs={
                "class": "textarea",
                "rows": 5,
                "placeholder": "Describe any additional requirements such as documentation, age restrictions, parole status, employment readiness level, or other prerequisites.",
            }),
            "average_served_per_month": forms.NumberInput(attrs={"class": "input", "placeholder": "e.g., 120", "min": "0"}),
            "intake_process_description": forms.Textarea(attrs={"class": "textarea", "rows": 4, "placeholder": "Describe your intake process"}),
            "partnership_reason": forms.Textarea(attrs={"class": "textarea", "rows": 4, "placeholder": "Why do you want to partner with ReRoute?"}),
            "reroute_support_needs": forms.Textarea(attrs={"class": "textarea", "rows": 4, "placeholder": "How can ReRoute support your mission?"}),
            "logo": forms.ClearableFileInput(attrs={"class": "input"}),
        }

    def __init__(self, *args, **kwargs):
        self.require_strict = kwargs.pop("require_strict", True)
        super().__init__(*args, **kwargs)
        if not self.require_strict:
            for field in self.fields.values():
                field.required = False
            self.fields["accuracy_confirmation"].required = False
            self.fields["terms_privacy_agreement"].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not self.require_strict:
            return cleaned_data

        required_fields = [
            "organization_name",
            "primary_contact_name",
            "contact_email",
            "contact_phone",
            "physical_address",
            "service_area",
            "year_founded",
            "organization_type",
            "average_served_per_month",
            "intake_process_description",
            "referral_method_preference",
            "partnership_reason",
            "reroute_support_needs",
        ]
        for field_name in required_fields:
            value = cleaned_data.get(field_name)
            if value in (None, "", []):
                self.add_error(field_name, "This field is required.")

        if not cleaned_data.get("services_offered"):
            self.add_error("services_offered", "Select at least one service.")
        if not cleaned_data.get("accuracy_confirmation"):
            self.add_error("accuracy_confirmation", "You must confirm application accuracy.")
        if not cleaned_data.get("terms_privacy_agreement"):
            self.add_error("terms_privacy_agreement", "You must agree to terms and privacy.")
        return cleaned_data
