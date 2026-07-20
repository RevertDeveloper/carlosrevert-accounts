from django.core.management.base import BaseCommand

from apps.plans.services import assign_plan
from apps.users.models import User


class Command(BaseCommand):
    help = "Create development-only demo users. Never run automatically in production."

    def handle(self, *args, **options):
        records = (
            ("demo-free", "demo-free@example.test", "FREE", False),
            ("demo-premium", "demo-premium@example.test", "PREMIUM", False),
            ("demo-admin", "demo-admin@example.test", "PREMIUM", True),
        )
        for username, email, plan, staff in records:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "is_staff": staff, "is_superuser": staff},
            )
            if created:
                user.set_password("ChangeThisDemoPassword123!")
                user.save()
            assign_plan(user, plan, reason="Usuario de demostración")
            self.stdout.write(
                self.style.SUCCESS(f"{'Created' if created else 'Updated'} {username}")
            )
