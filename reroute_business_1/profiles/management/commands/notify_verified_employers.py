from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from reroute_business.profiles.models import EmployerProfile

class Command(BaseCommand):
    help = (
        "Send a simple notification email to verified employers. "
        "By default, emails go to employers verified within the last 7 days."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--since-days",
            type=int,
            default=7,
            help="Only notify employers verified within the last N days (default: 7). Use 0 to notify all verified employers.",
        )

    def handle(self, *args, **options):
        since_days = int(options.get("since_days", 7))

        qs = EmployerProfile.objects.filter(verified=True)
        if since_days > 0:
            cutoff = timezone.now() - timezone.timedelta(days=since_days)
            qs = qs.filter(verified_at__gte=cutoff)

        count_sent = 0
        for prof in qs.select_related("user"):
            email = getattr(prof.user, "email", None)
            if not email:
                continue
            try:
                send_mail(
                    subject="Your ReRoute employer account is verified",
                    message=(
                        "Hi,\n\n"
                        "Your employer account on ReRoute has been verified.\n"
                        "You can now post jobs and contact candidates.\n\n"
                        "Dashboard: https://www.reroutejobs.com/employer/dashboard/\n\n"
                        "— ReRoute Team"
                    ),
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[email],
                    fail_silently=True,
                )
                count_sent += 1
            except Exception:
                # Best-effort: skip on error
                continue

        self.stdout.write(self.style.SUCCESS(f"Notified {count_sent} employer(s)."))
