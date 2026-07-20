from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.CreateModel(name="ClientApplication", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=100)), ("slug", models.SlugField(unique=True)), ("base_url", models.URLField()), ("is_active", models.BooleanField(default=True)), ("consumes_quota", models.BooleanField(default=True)), ("service_key_hash", models.CharField(blank=True, max_length=128)), ("created_at", models.DateTimeField(auto_now_add=True))], options={"ordering": ("name",)})]
