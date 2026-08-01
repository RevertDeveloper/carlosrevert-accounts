from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailVerificationChallenge",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("code_hash", models.CharField(max_length=128, verbose_name="hash del código")),
                ("expires_at", models.DateTimeField(verbose_name="expira el")),
                ("attempts", models.PositiveSmallIntegerField(default=0, verbose_name="intentos")),
                ("sent_at", models.DateTimeField(verbose_name="enviado el")),
                (
                    "consumed_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="consumido el"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="creado el")),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_verification_challenge",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="usuario",
                    ),
                ),
            ],
            options={
                "verbose_name": "desafío de verificación de correo",
                "verbose_name_plural": "desafíos de verificación de correo",
                "ordering": ("-created_at",),
            },
        ),
    ]
