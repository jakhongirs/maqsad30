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
    calendar_icon = models.ImageField(
        _("Calendar Icon"), upload_to="challenge_calendar_icons/", null=True, blank=True
    )
    award_icon = models.ImageField(
        _("Award Icon"), upload_to="award_icons/", null=True, blank=True
    )
    video_instruction_url = models.URLField(_("Video instruction URL"))
    video_instruction_title = models.CharField(
        _("Video instruction title"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Title for the instruction video"),
    )
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


class Tournament(BaseModel):
    title = models.CharField(_("Title"), max_length=255)
    icon = models.ImageField(_("Icon"), upload_to="tournament_icons/")
    award_icon = models.ImageField(
        _("Award Icon"), upload_to="tournament_award_icons/", null=True, blank=True
    )
    finish_date = models.DateTimeField(_("Finish Date"))
    challenges = models.ManyToManyField(
        Challenge,
        related_name="tournaments",
        verbose_name=_("Challenges"),
    )
    is_active = models.BooleanField(_("Is Active"), default=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Tournament")
        verbose_name_plural = _("Tournaments")


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
    challenge = models.OneToOneField(
        Challenge, on_delete=models.CASCADE, related_name="award", null=True, blank=True
    )

    def __str__(self):
        return f"Award for {self.challenge.title}"


class TournamentAward(BaseModel):
    tournament = models.OneToOneField(
        Tournament, on_delete=models.CASCADE, related_name="award"
    )

    def __str__(self):
        return f"Award for {self.tournament.title}"

    class Meta:
        verbose_name = _("Tournament Award")
        verbose_name_plural = _("Tournament Awards")


class UserAward(BaseModel):
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="awards"
    )
    challenge_award = models.ForeignKey(
        ChallengeAward,
        on_delete=models.CASCADE,
        related_name="user_awards",
        null=True,
        blank=True,
    )
    tournament_award = models.ForeignKey(
        TournamentAward,
        on_delete=models.CASCADE,
        related_name="user_awards",
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = [("user", "challenge_award"), ("user", "tournament_award")]

    def __str__(self):
        if self.challenge_award:
            return (
                f"{self.user.first_name} - {self.challenge_award.challenge.title} Award"
            )
        return (
            f"{self.user.first_name} - {self.tournament_award.tournament.title} Award"
        )


class UserTournament(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_tournaments",
        verbose_name=_("User"),
    )
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name="user_tournaments",
        verbose_name=_("Tournament"),
    )
    consecutive_failures = models.PositiveIntegerField(
        _("Consecutive failures"), default=0
    )
    total_failures = models.PositiveIntegerField(_("Total failures"), default=0)
    is_failed = models.BooleanField(_("Is failed"), default=False)
    started_at = models.DateTimeField(_("Started at"), auto_now_add=True)

    class Meta:
        unique_together = ["user", "tournament"]
        verbose_name = _("User Tournament")
        verbose_name_plural = _("User Tournaments")

    def check_failure_conditions(self):
        """Check if tournament should be marked as failed based on failure conditions"""
        if self.consecutive_failures >= 2 or self.total_failures >= 2:
            self.is_failed = True
            self.save()
        return self.is_failed


class UserTournamentDay(BaseModel):
    user_tournament = models.ForeignKey(
        UserTournament,
        on_delete=models.CASCADE,
        related_name="daily_records",
        verbose_name=_("User Tournament"),
    )
    date = models.DateField(_("Date"))
    completed_challenges = models.ManyToManyField(
        Challenge,
        related_name="tournament_day_completions",
        verbose_name=_("Completed Challenges"),
    )
    is_completed = models.BooleanField(_("Is completed"), default=False)

    class Meta:
        unique_together = ["user_tournament", "date"]
        ordering = ["-date"]
        verbose_name = _("User Tournament Day")
        verbose_name_plural = _("User Tournament Days")

    def update_completion_status(self):
        """Update the day's completion status"""
        tournament_challenges = set(self.user_tournament.tournament.challenges.all())
        completed_challenges = set(self.completed_challenges.all())

        # Day is completed only if all tournament challenges are completed
        self.is_completed = completed_challenges == tournament_challenges
        self.save()

    @classmethod
    def process_day_end(cls, date):
        """
        Process end of day for all tournament days on the given date.
        Updates tournament failure counts based on complete day results.
        """
        # Get all tournament days for the given date
        day_records = cls.objects.filter(date=date).select_related("user_tournament")

        for day_record in day_records:
            # Update final completion status
            day_record.update_completion_status()

            if not day_record.is_completed:
                # Update tournament failure counts only if the day is actually failed
                tournament = day_record.user_tournament
                tournament.consecutive_failures += 1
                tournament.total_failures += 1
                tournament.save()
                tournament.check_failure_conditions()
            else:
                # Reset consecutive failures on successful completion
                tournament = day_record.user_tournament
                tournament.consecutive_failures = 0
                tournament.save()
