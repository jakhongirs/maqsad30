from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel

User = get_user_model()


class Question(BaseModel):
    title = models.CharField(_("Title"), max_length=255)
    order = models.PositiveIntegerField(_("Order"), default=0)
    is_active = models.BooleanField(_("Is active"), default=True)

    class Meta:
        ordering = ["order"]
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")

    def __str__(self):
        return self.title


class Answer(BaseModel):
    question = models.ForeignKey(
        Question,
        related_name="answers",
        verbose_name=_("Question"),
        on_delete=models.CASCADE,
    )
    text = models.CharField(_("Text"), max_length=255)
    order = models.PositiveIntegerField(_("Order"), default=0)
    is_active = models.BooleanField(_("Is active"), default=True)

    class Meta:
        ordering = ["order"]
        verbose_name = _("Answer")
        verbose_name_plural = _("Answers")

    def __str__(self):
        return f"{self.question.title} - {self.text}"


class UserAnswer(BaseModel):
    user = models.ForeignKey(
        User,
        related_name="onboarding_answers",
        verbose_name=_("User"),
        on_delete=models.CASCADE,
    )
    question = models.ForeignKey(
        Question,
        related_name="user_answers",
        verbose_name=_("Question"),
        on_delete=models.CASCADE,
    )
    answer = models.ForeignKey(
        Answer,
        related_name="user_selections",
        verbose_name=_("Answer"),
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ["user", "question"]
        verbose_name = _("User Answer")
        verbose_name_plural = _("User Answers")

    def __str__(self):
        return f"{self.user.username} - {self.question.title}"


class FAQ(BaseModel):
    question = models.CharField(_("Question"), max_length=255)
    answer = models.TextField(_("Answer"))
    order = models.PositiveIntegerField(_("Order"), default=0)
    is_active = models.BooleanField(_("Is active"), default=True)

    class Meta:
        ordering = ["order"]
        verbose_name = _("FAQ")
        verbose_name_plural = _("FAQs")

    def __str__(self):
        return self.question
