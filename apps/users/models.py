import os
from urllib.parse import urlparse

import requests
from django.contrib.auth.models import AbstractUser
from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.users.managers import SoftDeleteUserManager


class User(AbstractUser, BaseModel):
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
    objects = SoftDeleteUserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def download_telegram_photo(self):
        if self.telegram_photo_url and not self.telegram_photo:
            try:
                response = requests.get(self.telegram_photo_url)
                if response.status_code == 200:
                    # Get the filename from URL or use telegram_id
                    url_path = urlparse(self.telegram_photo_url).path
                    ext = (
                        os.path.splitext(url_path)[1] or ".jpg"
                    )  # Default to .jpg if no extension
                    filename = f"telegram_photo_{self.telegram_id}{ext}"

                    # Save the image
                    self.telegram_photo.save(
                        filename, ContentFile(response.content), save=True
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

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
