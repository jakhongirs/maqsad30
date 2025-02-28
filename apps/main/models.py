from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel

User = get_user_model()


class Challenge(BaseModel):
    title = models.CharField(_("Title"), max_length=255)
    icon = models.ImageField(_("Icon"), upload_to="challenge_icons/")
    video_instruction_url = models.URLField(_("Video instruction URL"))
    start_time = models.TimeField(_("Start time"))
    end_time = models.TimeField(_("End time"))

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError(_("End time must be after start time"))

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Challenge")
        verbose_name_plural = _("Challenges")


class UserChallenge(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_challenges",
        verbose_name=_("User"),
    )
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="user_challenges",
        verbose_name=_("Challenge"),
    )
    current_streak = models.PositiveIntegerField(_("Current streak"), default=0)
    highest_streak = models.PositiveIntegerField(_("Highest streak"), default=0)
    total_completions = models.PositiveIntegerField(_("Total completions"), default=0)
    last_completion_date = models.DateField(
        _("Last completion date"), null=True, blank=True
    )
    started_at = models.DateTimeField(_("Started at"), auto_now_add=True)

    class Meta:
        unique_together = ["user", "challenge"]
        ordering = ["-current_streak", "-highest_streak"]
        verbose_name = _("User Challenge")
        verbose_name_plural = _("User Challenges")

    def update_streak(self, completion_date):
        if self.last_completion_date:
            # Check if the completion is on the next day
            if completion_date == self.last_completion_date + timezone.timedelta(
                days=1
            ):
                self.current_streak += 1
            elif completion_date > self.last_completion_date:
                # Reset streak if there's a gap
                self.current_streak = 1
        else:
            # First completion
            self.current_streak = 1

        # Update highest streak if current streak is higher
        if self.current_streak > self.highest_streak:
            self.highest_streak = self.current_streak

        self.last_completion_date = completion_date
        self.total_completions += 1
        self.save()


class UserChallengeCompletion(BaseModel):
    user_challenge = models.ForeignKey(
        UserChallenge,
        on_delete=models.CASCADE,
        related_name="completions",
        verbose_name=_("User challenge"),
    )
    completed_at = models.DateTimeField(_("Completed at"), auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]
        verbose_name = _("User Challenge Completion")
        verbose_name_plural = _("User Challenge Completions")


class ChallengeAward(BaseModel):
    user_challenge = models.OneToOneField(
        UserChallenge,
        on_delete=models.CASCADE,
        related_name="award",
        verbose_name=_("User challenge"),
    )
    awarded_at = models.DateTimeField(_("Awarded at"), auto_now_add=True)

    class Meta:
        ordering = ["-awarded_at"]
        verbose_name = _("Challenge Award")
        verbose_name_plural = _("Challenge Awards")
