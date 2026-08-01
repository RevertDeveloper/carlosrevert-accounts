from django.core.management.base import BaseCommand

from apps.plans.models import Plan


class Command(BaseCommand):
    help = "Crea o actualiza los planes de acceso de demostración y premium."

    def handle(self, *args, **options):
        for code, name, limit in (
            ("FREE", "Acceso de demostración", 5),
            ("PREMIUM", "Premium", 20),
        ):
            plan, created = Plan.objects.update_or_create(
                code=code,
                defaults={"name": name, "daily_interaction_limit": limit, "is_active": True},
            )
            self.stdout.write(
                self.style.SUCCESS(f"{'Created' if created else 'Updated'} {plan.code}")
            )
