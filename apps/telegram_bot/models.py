from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomMessage(models.Model):
    title = models.CharField(_("Title"), max_length=255, null=True, blank=True)
    message = models.TextField(_("Message"))
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    sent = models.BooleanField(_("Sent"), default=False)
    sent_at = models.DateTimeField(_("Sent at"), null=True, blank=True)
    is_attach_link = models.BooleanField(_("Is attach link"), default=False)

    def __str__(self):
        return f"{self.id} - {self.created_at}"

    class Meta:
        verbose_name = _("Custom Message")
        verbose_name_plural = _("Custom Messages")
        ordering = ["-created_at"]
