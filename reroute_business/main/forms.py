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
from profiles.models import UserProfile
from django.contrib.auth.forms import PasswordChangeForm
from profiles.constants import USER_STATUS_CHOICES


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
