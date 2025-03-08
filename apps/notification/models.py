from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.main.models import Challenge, Tournament

User = get_user_model()


class NotificationTemplate(BaseModel):
    NOTIFICATION_TYPES = (
        ("challenge_reminder", _("Challenge Reminder")),
        ("tournament_daily", _("Tournament Daily Reminder")),
        ("tournament_missed", _("Tournament Missed Day")),
        ("tournament_failed", _("Tournament Failed")),
    )

    type = models.CharField(_("Type"), max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(_("Title"), max_length=255, null=True, blank=True)
    message = models.TextField(_("Message"))
    challenge = models.OneToOneField(
        Challenge,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_template",
    )
    tournament = models.OneToOneField(
        Tournament,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_template",
    )

    class Meta:
        verbose_name = _("Notification Template")
        verbose_name_plural = _("Notification Templates")

    def __str__(self):
        if self.challenge:
            return f"{self.get_type_display()} - {self.challenge.title}"
        elif self.tournament:
            return f"{self.get_type_display()} - {self.tournament.title}"
        return self.get_type_display()


class Notification(BaseModel):
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    sent_at = models.DateTimeField(_("Sent at"), auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")

    def __str__(self):
        return f"{self.template} - {self.user}"
