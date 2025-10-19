# ============================
# models.py (drop-in replacement)
# ============================
from __future__ import annotations

import uuid
from datetime import datetime
from django.db import models, transaction
from django.contrib.auth.models import User
from django.db.models import JSONField

# NOTE: If these imports live under a different app, update imports accordingly
from profiles.constants import USER_STATUS_CHOICES, YES_NO
from core.models import Skill


class UserProfile(models.Model):
    """
    User-owned profile for job seekers.
    We DO NOT add a DB field for role here to avoid a migration today.
    Instead, we expose properties that infer role from existing data:
      - Presence of EmployerProfile (preferred)
      - OR membership in Group('Employer' or 'Employers')
    """

    # --- Core link ---
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # --- Skills owned by the user (kept) ---
    skills = models.ManyToManyField(Skill, blank=True)

    # --- Step 1: Basic Profile Details ---
    firstname = models.CharField(max_length=50, blank=True)
    lastname = models.CharField(max_length=50, blank=True)
    preferred_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    personal_email = models.EmailField(blank=True)
    street_address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)

    # --- Step 2: Additional Info ---
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    background_image = models.ImageField(upload_to='users/backgrounds/', blank=True, null=True)
    birthdate = models.DateField(blank=True, null=True)
    pronouns = models.CharField(max_length=50, blank=True)
    native_language = models.CharField(max_length=100, blank=True)
    year_of_incarceration = models.IntegerField(blank=True, null=True)
    year_released = models.IntegerField(blank=True, null=True)
    relation_to_reroute = models.CharField(max_length=100, blank=True)

    # --- Step 3: Emergency Contact ---
    emergency_contact_firstname = models.CharField(max_length=100, blank=True)
    emergency_contact_lastname = models.CharField(max_length=100, blank=True)
    emergency_contact_relationship = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_email = models.EmailField(blank=True)

    # --- Step 4: Demographics ---
    gender = models.CharField(max_length=50, blank=True)
    ethnicity = models.CharField(max_length=50, blank=True)
    race = JSONField(default=list, blank=True, null=True)

    disability = models.CharField(max_length=3, choices=YES_NO, blank=True, null=True)
    veteran_status = models.CharField(max_length=3, choices=YES_NO, blank=True, null=True)
    disability_explanation = models.TextField(blank=True, null=True)
    veteran_explanation = models.TextField(blank=True, null=True)

    # --- User journey status ---
    status = models.CharField(
        max_length=30,
        choices=USER_STATUS_CHOICES,
        blank=True,
        help_text="User-defined status reflecting their current journey.",
    )

    # --- Platform account control (NOT A ROLE FIELD) ---
    account_status = models.CharField(
        max_length=20,
        default='active',
        choices=[('active', 'Active'), ('inactive', 'Inactive'), ('suspended', 'Suspended')],
        help_text="Platform-controlled account state.",
    )

    # Verified badge for public profile
    verified = models.BooleanField(default=True, help_text="Show a verified badge on this user's public profile.")

    work_in_us = models.CharField(max_length=10, choices=YES_NO, blank=True)
    sponsorship_needed = models.CharField(max_length=10, choices=YES_NO, blank=True)
    lgbtq = models.CharField(max_length=10, choices=YES_NO, blank=True)

    # --- Auto-generated ReRoute User ID (RR-YYYY-XXXXXX) ---
    user_uid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)

    # =========================
    # Computed role properties
    # =========================
    @property
    def is_employer(self) -> bool:
        """Treat someone as employer if they own an EmployerProfile or are in Employer group(s)."""
        try:
            # Presence of employer profile is the strongest signal (OneToOne)
            if hasattr(self.user, 'employerprofile') and self.user.employerprofile:
                return True
        except Exception:
            pass
        try:
            return self.user.groups.filter(name__in=["Employer", "Employers"]).exists()
        except Exception:
            return False

    @property
    def account_type(self) -> str:
        """Human readable role: 'employer' vs 'seeker'. Keeps templates simple."""
        return "employer" if self.is_employer else "seeker"

    # =========================
    # ID generation
    # =========================
    def save(self, *args, **kwargs):
        if not self.user_uid:
            self.user_uid = self.generate_uid()
        super().save(*args, **kwargs)

    def generate_uid(self) -> str:
        if self.user and self.user.id and getattr(self.user, 'date_joined', None):
            return f"RR-{self.user.date_joined.year}-{self.user.id:06d}"
        year = datetime.now().year
        with transaction.atomic():
            count = UserProfile.objects.filter(user_uid__startswith=f"RR-{year}").count() + 1
            return f"RR-{year}-TEMP{count:06d}"

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    class Meta:
        ordering = ['user_uid']
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class EmployerProfile(models.Model):
    """
    Separate employer entity tied 1:1 to a User. Its mere existence implies the user is an employer.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employerprofile')
    company_name = models.CharField(max_length=255)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    # Company logo (employer profile picture). Note: update upload_to path per request.
    logo = models.ImageField(upload_to='employers/logos/', blank=True, null=True)
    # Optional hero background image for public/employer views
    background_image = models.ImageField(upload_to='employers/backgrounds/', blank=True, null=True)

    # Manual verification to prevent spam/fake listings
    verified = models.BooleanField(default=False, help_text="Manually verified by ReRoute staff")
    verified_at = models.DateTimeField(blank=True, null=True)
    verification_notes = models.TextField(blank=True, help_text="Internal notes for verification decisions")

    def __str__(self):
        return self.company_name


# -----------------------------
# Subscription
# -----------------------------
class Subscription(models.Model):
    """
    Subscription linked 1:1 to the Django User.
    - For job seekers, plan_name is always 'Free'.
    - For employers, plan_name is one of 'Basic', 'Pro', 'Enterprise'.
    - Employers may have an expiry_date; seekers typically do not.
    """

    PLAN_FREE = "Free"
    PLAN_BASIC = "Basic"
    PLAN_PRO = "Pro"
    PLAN_ENTERPRISE = "Enterprise"

    PLAN_CHOICES = [
        (PLAN_FREE, "Free"),
        (PLAN_BASIC, "Basic"),
        (PLAN_PRO, "Pro"),
        (PLAN_ENTERPRISE, "Enterprise"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    plan_name = models.CharField(max_length=32, choices=PLAN_CHOICES, default=PLAN_FREE)
    start_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(blank=True, null=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"Subscription({self.user.username}: {self.plan_name})"

    @property
    def is_free(self) -> bool:
        return self.plan_name == self.PLAN_FREE

    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
