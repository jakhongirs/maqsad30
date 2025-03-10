# Generated by Django 5.1.6 on 2025-02-28 13:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="full_name",
        ),
        migrations.AddField(
            model_name="user",
            name="first_name",
            field=models.CharField(
                blank=True, max_length=32, null=True, verbose_name="First name"
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="last_name",
            field=models.CharField(
                blank=True, max_length=32, null=True, verbose_name="Last name"
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="telegram_id",
            field=models.CharField(
                blank=True,
                max_length=32,
                null=True,
                unique=True,
                verbose_name="Telegram ID",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="telegram_photo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="telegram_photos/",
                verbose_name="Telegram Photo",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="telegram_photo_url",
            field=models.URLField(
                blank=True, max_length=255, null=True, verbose_name="Telegram Photo URL"
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="telegram_username",
            field=models.CharField(
                blank=True, max_length=32, null=True, verbose_name="Telegram Username"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                blank=True, max_length=254, null=True, unique=True, verbose_name="Email"
            ),
        ),
    ]
