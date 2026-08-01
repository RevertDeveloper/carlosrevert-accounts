from django.db import migrations


def mark_existing_emails_verified(apps, schema_editor):  # type: ignore[no-untyped-def]
    User = apps.get_model("users", "User")
    User.objects.filter(email_verified=False).update(email_verified=True)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_alter_user_accepted_terms_at_alter_user_created_at_and_more"),
    ]

    operations = [migrations.RunPython(mark_existing_emails_verified, migrations.RunPython.noop)]
