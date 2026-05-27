# Generated manually on 2026-05-26

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_alter_user_is_staff"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("legal_name", models.CharField(default="AML Check Enterprise", max_length=255)),
                ("trading_name", models.CharField(blank=True, max_length=255)),
                ("tax_id", models.CharField(blank=True, max_length=80)),
                ("registration_number", models.CharField(blank=True, max_length=80)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("city", models.CharField(blank=True, max_length=120)),
                ("country", models.CharField(blank=True, max_length=120)),
                ("phone", models.CharField(blank=True, max_length=80)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("website", models.URLField(blank=True)),
                ("compliance_officer", models.CharField(blank=True, max_length=160)),
                ("report_footer", models.CharField(blank=True, max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Company profile",
                "verbose_name_plural": "Company profile",
            },
        ),
    ]
