from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("usage", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="usageevent",
            name="validated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="usageevent",
            name="status",
            field=models.CharField(
                choices=[
                    ("authorized", "Authorized"),
                    ("processing", "Processing"),
                    ("completed", "Completed"),
                    ("failed", "Failed"),
                    ("rejected_quota", "Rejected by quota"),
                    ("rejected_auth", "Rejected by authentication"),
                    ("cancelled", "Cancelled"),
                ],
                max_length=30,
            ),
        ),
    ]
