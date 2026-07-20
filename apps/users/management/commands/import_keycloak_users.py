import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.users.models import User


class Command(BaseCommand):
    help = "Idempotently import permitted Keycloak CSV identity data without passwords."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=Path)

    def handle(self, *args, **options):
        source = options["csv_file"]
        if not source.is_file():
            raise CommandError(f"File not found: {source}")
        created = updated = skipped = 0
        with source.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                username, email = (
                    row.get("username", "").strip(),
                    row.get("email", "").strip().lower(),
                )
                if not username or not email:
                    skipped += 1
                    continue
                user, was_created = User.objects.update_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "first_name": row.get("first_name", ""),
                        "last_name": row.get("last_name", ""),
                        "is_active": False,
                    },
                )
                user.set_unusable_password()
                user.save(update_fields=("password",))
                created += int(was_created)
                updated += int(not was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"created={created} updated={updated} skipped={skipped}; "
                "imported accounts require password activation."
            )
        )
