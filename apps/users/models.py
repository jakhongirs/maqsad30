import io

import requests
from django.contrib.auth.models import AbstractUser
from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import gettext_lazy as _
from PIL import Image

from apps.common.models import BaseModel
from apps.users.managers import SoftDeleteUserManager


class Timezone(BaseModel):
    name = models.CharField(_("Name"), max_length=100)
    offset = models.CharField(_("GMT Offset"), max_length=10)

    def __str__(self):
        return f"{self.name} ({self.offset})"

    class Meta:
        verbose_name = _("Timezone")
        verbose_name_plural = _("Timezones")
        ordering = ["offset"]


class User(AbstractUser, BaseModel):
    LANGUAGE_CHOICES = (
        ("en", _("English")),
        ("uz", _("Uzbek")),
        ("ru", _("Russian")),
        ("uz-cy", _("Uzbek Cyrillic")),
    )

    username = models.CharField(
        _("Username"), max_length=150, unique=True, null=True, blank=True
    )
    first_name = models.CharField(_("First name"), max_length=32, null=True, blank=True)
    last_name = models.CharField(_("Last name"), max_length=32, null=True, blank=True)
    is_deleted = models.BooleanField(_("Is deleted"), default=False)
    email = models.EmailField(_("Email"), unique=True, null=True, blank=True)
    telegram_id = models.CharField(
        _("Telegram ID"), max_length=32, unique=True, null=True, blank=True
    )
    telegram_username = models.CharField(
        _("Telegram Username"), max_length=32, null=True, blank=True
    )
    telegram_photo_url = models.URLField(
        _("Telegram Photo URL"), max_length=255, null=True, blank=True
    )
    telegram_photo = models.ImageField(
        _("Telegram Photo"), upload_to="telegram_photos/", null=True, blank=True
    )
    language = models.CharField(
        _("Language"), max_length=5, choices=LANGUAGE_CHOICES, default="uz"
    )
    timezone = models.ForeignKey(
        Timezone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name=_("Timezone"),
    )
    is_onboarding_finished = models.BooleanField(
        _("Is onboarding finished"), default=False
    )
    objects = SoftDeleteUserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def download_telegram_photo(self):
        if self.telegram_photo_url and not self.telegram_photo:
            try:
                # If it's an SVG URL, modify it to get PNG
                url = self.telegram_photo_url
                if url.endswith(".svg"):
                    # Replace the file extension and add size parameter
                    url = url.replace("/svg/", "/").replace(".svg", ".jpg")

                response = requests.get(url)
                if response.status_code == 200:
                    # Convert to RGB if needed and optimize
                    image = Image.open(io.BytesIO(response.content))
                    if image.mode in ("RGBA", "P"):
                        image = image.convert("RGB")

                    # Save as optimized JPEG
                    output = io.BytesIO()
                    image.save(output, format="JPEG", quality=95, optimize=True)
                    output.seek(0)

                    # Save to model
                    filename = f"telegram_photo_{self.telegram_id}.jpg"
                    self.telegram_photo.save(
                        filename, ContentFile(output.getvalue()), save=True
                    )

            except Exception as e:
                print(f"Error downloading telegram photo: {e}")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.telegram_photo_url:
            self.download_telegram_photo()

    def __str__(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        if self.email:
            return self.email

    def prepare_to_delete(self):
        self.is_deleted = True
        for x in ["email", "first_name", "last_name"]:
            if getattr(self, x):
                setattr(self, x, f"DELETED_{self.id}_{getattr(self, x)}")
        self.save()

    def check_channel_membership(self, bot_token, channel_id):
        """
        Check if the user is a member of a specified Telegram channel.

        Args:
            bot_token (str): Telegram bot token
            channel_id (str): Channel username or ID (e.g. "@channel_name")

        Returns:
            bool: True if user is a member, False otherwise
        """
        if not self.telegram_id:
            return False

        url = f"https://api.telegram.org/bot{bot_token}/getChatMember"
        params = {"chat_id": channel_id, "user_id": self.telegram_id}

        try:
            response = requests.get(url, params=params)
            data = response.json()

            if "result" in data:
                status = data["result"]["status"]
                return status in ["member", "administrator", "creator"]
            return False
        except Exception as e:
            print(f"Error checking channel membership: {e}")
            return False

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
