import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("applications", "0001_initial")]
    operations = [
        migrations.CreateModel(name="DailyUsage", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("date", models.DateField()), ("interaction_count", models.PositiveIntegerField(default=0)), ("updated_at", models.DateTimeField(auto_now=True)), ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="daily_usages", to=settings.AUTH_USER_MODEL))], options={"ordering": ("-date",)}),
        migrations.CreateModel(name="UsageEvent", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("request_id", models.UUIDField(default=uuid.uuid4, unique=True)), ("action", models.CharField(max_length=80)), ("status", models.CharField(choices=[("authorized", "Authorized"), ("completed", "Completed"), ("failed", "Failed"), ("rejected_quota", "Rejected by quota"), ("rejected_auth", "Rejected by authentication"), ("cancelled", "Cancelled")], max_length=30)), ("interaction_cost", models.PositiveIntegerField(default=1)), ("metadata", models.JSONField(blank=True, default=dict)), ("error_code", models.CharField(blank=True, max_length=80)), ("processing_time_ms", models.PositiveIntegerField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("completed_at", models.DateTimeField(blank=True, null=True)), ("application", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="usage_events", to="applications.clientapplication")), ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="usage_events", to=settings.AUTH_USER_MODEL))], options={"ordering": ("-created_at",)}),
        migrations.CreateModel(name="InteractionReservation", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("request_id", models.UUIDField(unique=True)), ("action", models.CharField(max_length=80)), ("created_at", models.DateTimeField(auto_now_add=True)), ("application", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="applications.clientapplication")), ("event", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="reservation", to="usage.usageevent")), ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL))]),
        migrations.AddConstraint(model_name="dailyusage", constraint=models.UniqueConstraint(fields=("user", "date"), name="unique_daily_usage_per_user")),
        migrations.AddIndex(model_name="usageevent", index=models.Index(fields=["user", "created_at"], name="usage_usage_user_id_40f9db_idx")),
        migrations.AddIndex(model_name="usageevent", index=models.Index(fields=["application", "status"], name="usage_app_status_idx")),
    ]
