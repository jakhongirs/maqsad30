# Generated by Django 5.1.6 on 2025-03-06 17:25

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0013_userchallengecompletion_is_active"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userchallengecompletion",
            name="is_active",
        ),
    ]
