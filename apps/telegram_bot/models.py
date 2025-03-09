from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.main.models import Challenge


class CustomMessage(models.Model):
    title = models.CharField(_("Title"), max_length=255, null=True, blank=True)
    message = models.TextField(_("Message"))
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Challenge"),
        related_name="custom_messages",
    )
    sent = models.BooleanField(_("Sent"), default=False)
    sent_at = models.DateTimeField(_("Sent at"), null=True, blank=True)
    is_attach_link = models.BooleanField(_("Is attach link"), default=False)

    def __str__(self):
        return f"{self.id} - {self.created_at}"

    def get_message_text(self):
        """
        Returns the formatted message text. If there's a title, it will be included.
        """
        text = ""
        if self.title:
            text += f"<b>{self.title}</b>\n\n"
        text += self.message
        return text

    class Meta:
        verbose_name = _("Custom Message")
        verbose_name_plural = _("Custom Messages")
        ordering = ["-created_at"]
