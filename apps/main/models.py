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
    is_active = models.BooleanField(_("Is active"), default=True)
    has_award = models.BooleanField(_("Has award"), default=False)

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
        if not self.last_completion_date or not self.is_active:
            return False

        today = timezone.now().date()
        completions = list(
            self.completions.filter(
                completed_at__gte=self.started_at,
                completed_at__date__lte=today,
                is_active=True,
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

    def reset_stats(self):
        """
        Reset the challenge stats but keep completion history
        """
        self.current_streak = 0
        self.started_at = timezone.now()
        self.save()

    def deactivate(self):
        """
        Deactivate the challenge but keep completion history
        """
        self.is_active = False
        self.save()

    def reactivate(self):
        """
        Reactivate the challenge and reset stats
        """
        self.is_active = True
        self.current_streak = 0
        self.started_at = timezone.now()
        self.save()

    def check_and_award_if_eligible(self):
        """
        Check if user has achieved 30-day streak and give award if eligible
        """
        if self.highest_streak >= 30 and not self.has_award:
            # Create award for the user
            challenge_award, created = ChallengeAward.objects.get_or_create(
                challenge=self.challenge
            )
            UserAward.objects.get_or_create(
                user=self.user, challenge_award=challenge_award
            )
            self.has_award = True
            self.save()
            return True
        return False

    def delete(self, *args, **kwargs):
        """
        Override delete to deactivate instead of deleting
        """
        # Instead of deleting, we deactivate the challenge
        self.deactivate()

    def update_streak(self, completion_date):
        # If challenge is not active, don't update streak
        if not self.is_active:
            return

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
        new_highest_streak = max(streak_lengths) if streak_lengths else 0

        # Update highest streak if the new one is higher
        if new_highest_streak > self.highest_streak:
            self.highest_streak = new_highest_streak

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

        # Check for 30-day streak achievement
        if self.highest_streak >= 30:
            self.check_and_award_if_eligible()

        # Check for challenge failure conditions
        if self.has_failed():
            self.reset_stats()
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


class ChallengeAward(BaseModel):
    challenge = models.OneToOneField(
        Challenge, on_delete=models.CASCADE, related_name="award", null=True, blank=True
    )

    def __str__(self):
        return f"Award for {self.challenge.title}"


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

    class Meta:
        unique_together = [("user", "challenge_award")]

    def __str__(self):
        return f"{self.user.first_name} - {self.challenge_award.challenge.title} Award"
