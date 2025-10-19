from django.db import models
from django.contrib.auth.models import User
from core.models import Skill

EXPERIENCE_LEVELS = [
    ('entry', 'Entry-level'),
    ('junior', 'Junior'),
    ('mid', 'Mid'),
    ('senior', 'Senior'),
    ('lead', 'Lead'),
]

class Job(models.Model):
    # New fields for detailed job card display
    JOB_TYPE_CHOICES = [
        ('full_time', 'Full-Time'),
        ('part_time', 'Part-Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('temporary', 'Temporary'),
    ]

    SALARY_TYPE_CHOICES = [
        ('year', 'Per Year'),
        ('hour', 'Per Hour'),
    ]


    title = models.CharField(max_length=200)
    description = models.TextField()
    requirements = models.TextField()
    location = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10, blank=True)
    employer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_jobs')
    employer_image = models.ImageField(upload_to='employer_logos/', blank=True, null=True)  # ✅ NEW
    tags = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)  # ✅ soft-delete flag
    created_at = models.DateTimeField(auto_now_add=True)
    skills_required = models.ManyToManyField(Skill, blank=True)
    is_flagged = models.BooleanField(default=False)
    flagged_reason = models.TextField(blank=True, null=True)

    job_type = models.CharField(
        max_length=20,
        choices=JOB_TYPE_CHOICES,
        default='full_time',
        help_text="e.g., Full-Time, Part-Time"
    )

    salary_min = models.IntegerField(
        blank=True,
        null=True,
        help_text="Minimum salary in thousands, e.g., 57 = $57k"
    )

    salary_max = models.IntegerField(
        blank=True,
        null=True,
        help_text="Maximum salary in thousands, e.g., 62 = $62k"
    )

    experience_level = models.CharField(
        max_length=20, choices=EXPERIENCE_LEVELS, blank=True
    )

    salary_type = models.CharField(max_length=10, choices=SALARY_TYPE_CHOICES, default='year')

    hourly_min = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )  # e.g., 18.50

    hourly_max = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    
    currency = models.CharField(max_length=3, default='USD', blank=True)


    def __str__(self):
      if self.employer:
          return f"{self.title} at {self.employer.username}"
      return self.title


class SavedJob(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job = models.ForeignKey('Job', on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'job')  # Prevent duplicate saves

    def __str__(self):
        return f"{self.user.username} saved {self.job.title}"


class ArchivedJob(models.Model):
    """Jobs a user archived from their Saved list.

    Lightweight table to avoid altering SavedJob schema; archiving moves a row
    from SavedJob -> ArchivedJob, and unarchiving reverses it.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job = models.ForeignKey('Job', on_delete=models.CASCADE)
    archived_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('user', 'job')

    def __str__(self):
        return f"{self.user.username} archived {self.job.title}"

class Application(models.Model):
    # Foreign key to user applying
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')

    # Foreign key to the job being applied to
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')

    # Status with controlled choices for clarity
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('interview', 'Interview'),
        ('rejected', 'Rejected'),
        ('accepted', 'Accepted'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')

    # Time submitted
    submitted_at = models.DateTimeField(auto_now_add=True)

    # Time last updated (e.g. status changed)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.applicant.username} applied to {self.job.title}"
