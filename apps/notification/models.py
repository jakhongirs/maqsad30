from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.main.models import Challenge, SuperChallenge


class ChallengeNotificationTemplate(BaseModel):
    """
    Template for notifications sent to users for regular challenges.
    This allows admins to customize the notification message for each challenge.
    """

    challenge = models.OneToOneField(
        Challenge,
        on_delete=models.CASCADE,
        related_name="notification_template",
        verbose_name=_("Challenge"),
    )
    message = models.TextField(
        _("Message"),
        help_text=_("Notification message to be sent to users at challenge start time"),
    )
    is_active = models.BooleanField(_("Is active"), default=True)

    def __str__(self):
        return f"Notification for {self.challenge.title}"

    class Meta:
        verbose_name = _("Challenge Notification Template")
        verbose_name_plural = _("Challenge Notification Templates")


class SuperChallengeNotificationTemplate(BaseModel):
    """
    Template for notifications sent to users for super challenges.
    """

    super_challenge = models.OneToOneField(
        SuperChallenge,
        on_delete=models.CASCADE,
        related_name="notification_template",
        verbose_name=_("Super Challenge"),
    )
    general_message = models.TextField(
        _("General Message"),
        help_text=_("General notification message sent to active users"),
    )
    progress_warning_message = models.TextField(
        _("Progress Warning Message"),
        help_text=_("Warning message sent when user hasn't completed all challenges"),
    )
    failure_message = models.TextField(
        _("Failure Message"),
        help_text=_("Message sent when user has failed the super challenge"),
    )
    is_active = models.BooleanField(_("Is active"), default=True)

    def __str__(self):
        return f"Notification for {self.super_challenge.title}"

    class Meta:
        verbose_name = _("Super Challenge Notification Template")
        verbose_name_plural = _("Super Challenge Notification Templates")


class NotificationLog(BaseModel):
    """
    Log of notifications sent to users.
    """

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notification_logs",
        verbose_name=_("User"),
    )
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_logs",
        verbose_name=_("Challenge"),
    )
    super_challenge = models.ForeignKey(
        SuperChallenge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_logs",
        verbose_name=_("Super Challenge"),
    )
    message = models.TextField(_("Message"))
    notification_type = models.CharField(
        _("Notification Type"),
        max_length=50,
        choices=[
            ("challenge", _("Challenge")),
            ("super_challenge_general", _("Super Challenge General")),
            ("super_challenge_warning", _("Super Challenge Warning")),
            ("super_challenge_failure", _("Super Challenge Failure")),
        ],
    )
    sent_at = models.DateTimeField(_("Sent at"), auto_now_add=True)
    is_sent = models.BooleanField(_("Is sent"), default=False)
    error_message = models.TextField(_("Error Message"), null=True, blank=True)

    def __str__(self):
        return f"Notification to {self.user} at {self.sent_at}"

    class Meta:
        verbose_name = _("Notification Log")
        verbose_name_plural = _("Notification Logs")
        ordering = ["-sent_at"]
