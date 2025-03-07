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
    rules = models.TextField(_("Rules"), null=True, blank=True)

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
    start_date = models.DateTimeField(_("Start Date"), null=True, blank=True)
    finish_date = models.DateTimeField(_("Finish Date"), null=True, blank=True)
    challenges = models.ManyToManyField(
        Challenge,
        related_name="tournaments",
        verbose_name=_("Challenges"),
    )
    is_active = models.BooleanField(_("Is Active"), default=True)

    def clean(self):
        if self.start_date >= self.finish_date:
            raise ValidationError(_("Finish date must be after start date"))

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

    def has_failed(self):
        """
        Check if the challenge has failed based on the conditions:
        1. Two consecutive days missed
        2. Two days missed in total
        """
        if not self.last_completion_date:
            return False

        today = timezone.now().date()
        completions = list(
            self.completions.filter(
                completed_at__gte=self.started_at, completed_at__date__lte=today
            )
            .order_by("completed_at__date")
            .values_list("completed_at", flat=True)
        )

        if not completions:
            return False

        # Convert to dates and remove duplicates
        completion_dates = sorted(list({c.date() for c in completions}))

        # Check for two consecutive missed days
        for i in range(len(completion_dates) - 1):
            date_diff = (completion_dates[i + 1] - completion_dates[i]).days
            if (
                date_diff > 2
            ):  # More than 2 days between completions means 2 consecutive days missed
                return True

        # Check for total missed days
        start_date = completion_dates[0]
        end_date = completion_dates[-1]
        total_days = (end_date - start_date).days + 1
        completed_days = len(completion_dates)
        missed_days = total_days - completed_days

        return missed_days >= 2

    def delete(self, *args, **kwargs):
        """
        Override delete to handle special case of 30-day streak
        """
        # Check if we have a 30-day streak before deleting
        has_thirty_day_streak = self.highest_streak >= 30

        if has_thirty_day_streak:
            # If there's a 30-day streak, keep the completions but mark them as inactive
            self.completions.update(is_active=False)
            super().delete(*args, **kwargs)
        else:
            # If no 30-day streak, delete everything
            self.completions.all().delete()
            super().delete(*args, **kwargs)

    def update_streak(self, completion_date):
        # Get all completions for this user challenge
        completions = self.completions.filter(is_active=True)

        # Extract unique dates from completions
        completion_dates = {
            completion.completed_at.date() for completion in completions
        }

        # Filter out any future dates (should not happen, but just in case)
        today = timezone.now().date()
        completion_dates = {date for date in completion_dates if date <= today}

        # Convert to list and sort
        completion_dates = sorted(list(completion_dates))

        # If no completions, set streak to 0 and return
        if not completion_dates:
            self.current_streak = 0
            self.highest_streak = 0
            self.total_completions = 0
            self.save()
            return

        # Calculate streaks by identifying consecutive date groups
        streaks = []
        current_group = [completion_dates[0]]

        # Group consecutive dates
        for i in range(1, len(completion_dates)):
            current_date = completion_dates[i]
            previous_date = completion_dates[i - 1]

            # If dates are consecutive
            if current_date == previous_date + timezone.timedelta(days=1):
                current_group.append(current_date)
            else:
                # End of a streak, start a new group
                streaks.append(current_group)
                current_group = [current_date]

        # Add the last group
        if current_group:
            streaks.append(current_group)

        # Calculate streak lengths
        streak_lengths = [len(group) for group in streaks]

        # The highest streak is the length of the longest consecutive group
        self.highest_streak = max(streak_lengths) if streak_lengths else 0

        # The current streak is the length of the most recent group (if it includes today or yesterday)
        latest_group = streaks[-1] if streaks else []
        latest_date = latest_group[-1] if latest_group else None

        if latest_date and (
            latest_date == today or latest_date == today - timezone.timedelta(days=1)
        ):
            self.current_streak = len(latest_group)
        else:
            # If the latest group doesn't include today or yesterday, current streak is 0
            self.current_streak = 0

        # Update last completion date
        self.last_completion_date = completion_dates[-1]

        # Update total completions based on the number of unique completion dates
        self.total_completions = len(completion_dates)

        # Check for challenge failure conditions
        if self.has_failed():
            self.delete()
        else:
            self.save()


class UserChallengeCompletion(BaseModel):
    user_challenge = models.ForeignKey(
        UserChallenge,
        on_delete=models.CASCADE,
        related_name="completions",
        verbose_name=_("User challenge"),
    )
    completed_at = models.DateTimeField(_("Completed at"))
    is_active = models.BooleanField(_("Is Active"), default=True)

    def save(self, *args, **kwargs):
        if not self.completed_at:
            self.completed_at = timezone.localtime()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-completed_at"]
        verbose_name = _("User Challenge Completion")
        verbose_name_plural = _("User Challenge Completions")


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
    user_challenge = models.ForeignKey(
        UserChallenge,
        on_delete=models.CASCADE,
        related_name="user_tournaments",
        verbose_name=_("User challenge"),
        null=True,
        blank=True,
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

    def update_failures(self, check_date=None):
        """
        Update failure counts based on tournament day records.
        Similar to update_streak, this calculates consecutive and total failures dynamically.
        """
        if check_date is None:
            check_date = timezone.now().date()

        # Get all days within tournament period up to check_date
        day_records = (
            self.daily_records.filter(
                date__gte=self.tournament.start_date.date(),
                date__lte=min(check_date, self.tournament.finish_date.date()),
            )
            .order_by("date")
            .values_list("date", "is_completed")
        )

        # Convert to list of tuples (date, is_completed)
        day_records = list(day_records)

        if not day_records:
            self.consecutive_failures = 0
            self.total_failures = 0
            self.save()
            return

        # Calculate total failures
        self.total_failures = sum(1 for _, completed in day_records if not completed)

        # Calculate consecutive failures by looking at the most recent sequence
        consecutive = 0
        for _, completed in reversed(day_records):
            if not completed:
                consecutive += 1
            else:
                break

        self.consecutive_failures = consecutive
        self.save()
        self.check_failure_conditions()

    @classmethod
    def process_day_end(cls, date):
        """
        Process end of day for all tournaments on the given date.
        """
        # Get all active tournaments for the given date
        active_tournaments = cls.objects.filter(
            tournament__start_date__date__lte=date,
            tournament__finish_date__date__gte=date,
            is_failed=False,
        ).select_related("tournament")

        for user_tournament in active_tournaments:
            # Update completion status for the day
            day_record = user_tournament.daily_records.filter(date=date).first()
            if day_record:
                day_record.update_completion_status()

            # Update failure counts
            user_tournament.update_failures(date)


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
