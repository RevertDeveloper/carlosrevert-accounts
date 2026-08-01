from django.db import migrations


def rename_default_plan(apps, schema_editor):
    Plan = apps.get_model("plans", "Plan")
    Plan.objects.filter(code="FREE").update(name="Acceso de demostración")


def restore_default_plan_name(apps, schema_editor):
    Plan = apps.get_model("plans", "Plan")
    Plan.objects.filter(code="FREE").update(name="Free")


class Migration(migrations.Migration):
    dependencies = [("plans", "0005_alter_planchangelog_created_at")]

    operations = [
        migrations.RunPython(rename_default_plan, restore_default_plan_name),
    ]
