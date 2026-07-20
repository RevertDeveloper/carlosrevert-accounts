from django.core.management.base import BaseCommand

from apps.applications.models import ClientApplication


class Command(BaseCommand):
    help = "Create or update the known public applications."

    applications = (
        ("Home", "home", "https://carlosrevert.es", False),
        ("Juridia", "juridia", "https://juridia.carlosrevert.es", True),
        ("CLARK", "clark", "https://clark.carlosrevert.es", True),
        ("Transcriptor", "transcriptor", "https://transcriptor.carlosrevert.es", True),
    )

    def handle(self, *args, **options):
        for name, slug, base_url, consumes_quota in self.applications:
            application, created = ClientApplication.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "base_url": base_url,
                    "consumes_quota": consumes_quota,
                    "is_active": True,
                },
            )
            self.stdout.write(
                self.style.SUCCESS(f"{'Created' if created else 'Updated'} {application.slug}")
            )
