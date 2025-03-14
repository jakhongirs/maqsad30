# Generated by Django 5.1.6 on 2025-02-28 21:50

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_timezone_user_language_user_timezone"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_onboarding_finished",
            field=models.BooleanField(
                default=False, verbose_name="Is onboarding finished"
            ),
        ),
    ]
