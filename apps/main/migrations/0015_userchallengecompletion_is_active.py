# Generated by Django 5.1.6 on 2025-03-06 18:10

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0014_remove_userchallengecompletion_is_active"),
    ]

    operations = [
        migrations.AddField(
            model_name="userchallengecompletion",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Is Active"),
        ),
    ]
