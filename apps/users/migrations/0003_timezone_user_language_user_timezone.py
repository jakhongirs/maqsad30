# Generated by Django 5.1.6 on 2025-02-28 21:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_remove_user_full_name_user_first_name_user_last_name_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Timezone",
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
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                ("name", models.CharField(max_length=100, verbose_name="Name")),
                ("offset", models.CharField(max_length=10, verbose_name="GMT Offset")),
            ],
            options={
                "verbose_name": "Timezone",
                "verbose_name_plural": "Timezones",
                "ordering": ["offset"],
            },
        ),
        migrations.AddField(
            model_name="user",
            name="language",
            field=models.CharField(
                choices=[
                    ("en", "English"),
                    ("uz", "Uzbek"),
                    ("ru", "Russian"),
                    ("uz-cy", "Uzbek Cyrillic"),
                ],
                default="uz",
                max_length=5,
                verbose_name="Language",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="timezone",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="users",
                to="users.timezone",
                verbose_name="Timezone",
            ),
        ),
    ]
