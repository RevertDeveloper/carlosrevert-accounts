from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="Plan", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("code", models.CharField(max_length=30, unique=True)), ("name", models.CharField(max_length=80)), ("daily_interaction_limit", models.PositiveIntegerField()), ("is_active", models.BooleanField(default=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True))], options={"ordering": ("daily_interaction_limit", "code")}),
        migrations.CreateModel(name="UserPlan", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("assigned_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("assigned_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_plans", to=settings.AUTH_USER_MODEL)), ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="user_assignments", to="plans.plan")), ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="user_plan", to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name="PlanChangeLog", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("reason", models.CharField(blank=True, max_length=255)), ("created_at", models.DateTimeField(auto_now_add=True)), ("changed_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="plan_changes_made", to=settings.AUTH_USER_MODEL)), ("new_plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="new_logs", to="plans.plan")), ("previous_plan", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="previous_logs", to="plans.plan")), ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="plan_changes", to=settings.AUTH_USER_MODEL))], options={"ordering": ("-created_at",)}),
    ]
