from django.contrib import admin
from .models import UserProfile
from .models import EmployerProfile
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user', 'verified', 'verified_at')
    search_fields = ('company_name', 'user__username', 'user__email')
    list_filter = ('verified',)

    fieldsets = (
        ('Company Info', {
            'fields': ('user', 'company_name', 'website', 'logo', 'background_image', 'description')
        }),
        ('Verification', {
            'fields': ('verified', 'verified_at', 'verification_notes'),
        }),
    )

    readonly_fields = ('verified_at',)

    actions = ['mark_verified', 'mark_unverified', 'mark_verified_and_notify']

    def save_model(self, request, obj, form, change):
        # Update timestamp when flipping verified on
        if 'verified' in form.changed_data:
            if obj.verified and obj.verified_at is None:
                obj.verified_at = timezone.now()
            if not obj.verified:
                obj.verified_at = None
        super().save_model(request, obj, form, change)

    def mark_verified(self, request, queryset):
        updated = queryset.update(verified=True, verified_at=timezone.now())
        self.message_user(request, f"Marked {updated} employer(s) as verified.")
    mark_verified.short_description = "Mark selected employers as verified"

    def mark_unverified(self, request, queryset):
        updated = queryset.update(verified=False, verified_at=None)
        self.message_user(request, f"Marked {updated} employer(s) as unverified.")
    mark_unverified.short_description = "Mark selected employers as unverified"

    def mark_verified_and_notify(self, request, queryset):
        """Set verified=True and send a simple notification email to each employer."""
        count = 0
        for prof in queryset.select_related('user'):
            if not prof.verified:
                prof.verified = True
                prof.verified_at = timezone.now()
                prof.save(update_fields=['verified', 'verified_at'])
            # Send email (best-effort)
            try:
                to_addr = getattr(prof.user, 'email', None)
                if to_addr:
                    send_mail(
                        subject="Your ReRoute employer account is verified",
                        message=(
                            "Hi,\n\n"
                            "Great news — your employer account on ReRoute has been verified.\n"
                            "You can now post jobs and contact candidates.\n\n"
                            "Get started: https://www.reroutejobs.com/employer/dashboard/\n\n"
                            "— ReRoute Team"
                        ),
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                        recipient_list=[to_addr],
                        fail_silently=True,
                    )
                    count += 1
            except Exception:
                # Do not block the admin action on mail failures
                pass
        self.message_user(request, f"Verified and notified {count} employer(s).")
    mark_verified_and_notify.short_description = "Verify and notify selected employers"

