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


class SuperChallenge(BaseModel):
    """
    A Super Challenge is a collection of regular challenges that must all be completed
    on the same day for the super challenge to be considered completed for that day.
    """

    title = models.CharField(_("Title"), max_length=255)
    description = models.TextField(_("Description"), null=True, blank=True)
    icon = models.ImageField(_("Icon"), upload_to="super_challenge_icons/")
    calendar_icon = models.ImageField(
        _("Calendar Icon"),
        upload_to="super_challenge_calendar_icons/",
        null=True,
        blank=True,
    )
    award_icon = models.ImageField(
        _("Award Icon"), upload_to="super_challenge_award_icons/", null=True, blank=True
    )
    challenges = models.ManyToManyField(
        Challenge, related_name="super_challenges", verbose_name=_("Challenges")
    )
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"))

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(_("End date must be after start date"))

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Super Challenge")
        verbose_name_plural = _("Super Challenges")


class UserSuperChallenge(BaseModel):
    """
    Tracks a user's participation in a super challenge.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_super_challenges",
        verbose_name=_("User"),
    )
    super_challenge = models.ForeignKey(
        SuperChallenge,
        on_delete=models.CASCADE,
        related_name="user_super_challenges",
        verbose_name=_("Super Challenge"),
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
    is_failed = models.BooleanField(_("Is failed"), default=False)

    class Meta:
        unique_together = ["user", "super_challenge"]
        ordering = ["-current_streak", "-highest_streak"]
        verbose_name = _("User Super Challenge")
        verbose_name_plural = _("User Super Challenges")

    def has_failed(self):
        """
        Check if the super challenge has failed based on the conditions:
        1. Two consecutive days missed
        2. Two days missed in total

        This method considers all days from the super challenge start date
        (or user's started_at date, whichever is later) to yesterday (not including today).
        """
        if self.is_failed:
            return True

        today = timezone.now().date()
        yesterday = today - timezone.timedelta(days=1)

        # Check if the super challenge has ended
        if self.super_challenge.end_date < today:
            return False

        # Determine the start date for checking (later of super challenge start date or user started_at)
        challenge_start_date = self.super_challenge.start_date
        user_start_date = self.started_at.date()
        effective_start_date = max(challenge_start_date, user_start_date)

        # If yesterday is before the effective start date, no failure
        # This means the challenge just started today or hasn't started yet
        if yesterday < effective_start_date:
            return False

        # Get all completions for this user super challenge up to yesterday
        completions = self.completions.filter(
            completed_at__date__gte=effective_start_date,
            completed_at__date__lte=yesterday,
            is_active=True,
        ).order_by("completed_at__date")

        # Extract unique dates from completions
        completion_dates = {
            completion.completed_at.date() for completion in completions
        }

        # Create a set of all dates from effective_start_date to yesterday
        all_dates = set()
        current_date = effective_start_date
        while current_date <= yesterday:
            all_dates.add(current_date)
            current_date += timezone.timedelta(days=1)

        # Calculate missed dates
        missed_dates = all_dates - completion_dates

        # If there are no missed dates, no failure
        if not missed_dates:
            return False

        # Convert to sorted list for consecutive check
        missed_dates_list = sorted(list(missed_dates))

        # Check for two consecutive missed days
        has_consecutive_missed_days = False
        for i in range(len(missed_dates_list) - 1):
            if (missed_dates_list[i + 1] - missed_dates_list[i]).days == 1:
                has_consecutive_missed_days = True
                break

        # Check for total missed days
        has_two_missed_days = len(missed_dates) >= 2

        # If either condition is met, mark as failed
        if has_consecutive_missed_days or has_two_missed_days:
            # Mark as failed
            self.is_failed = True

            # Calculate streak information properly
            self.calculate_streak_before_failure()

            return True

        return False

    def get_failure_reason(self):
        """
        Returns the reason why the super challenge failed, including the specific missed days.
        Returns None if the challenge hasn't failed.
        """
        if not self.is_failed:
            return None

        today = timezone.now().date()

        # Determine the start date for checking
        challenge_start_date = self.super_challenge.start_date
        user_start_date = self.started_at.date()
        effective_start_date = max(challenge_start_date, user_start_date)

        # End date is either yesterday or the super challenge end date, whichever is earlier
        yesterday = today - timezone.timedelta(days=1)
        end_date = min(yesterday, self.super_challenge.end_date)

        # Get all completions for this user super challenge
        completions = self.completions.filter(
            completed_at__date__gte=effective_start_date,
            completed_at__date__lte=end_date,
            is_active=True,
        ).order_by("completed_at__date")

        # Extract unique dates from completions
        completion_dates = {
            completion.completed_at.date() for completion in completions
        }

        # Create a set of all dates from effective_start_date to end_date
        all_dates = set()
        current_date = effective_start_date
        while current_date <= end_date:
            all_dates.add(current_date)
            current_date += timezone.timedelta(days=1)

        # Calculate missed dates
        missed_dates = all_dates - completion_dates

        # If there are no missed dates (shouldn't happen for failed challenges)
        if not missed_dates:
            return {"failure_type": "unknown"}

        # Convert to sorted list
        missed_dates_list = sorted(list(missed_dates))

        # Check for two consecutive missed days
        consecutive_missed_days = []
        for i in range(len(missed_dates_list) - 1):
            if (missed_dates_list[i + 1] - missed_dates_list[i]).days == 1:
                consecutive_missed_days = [
                    missed_dates_list[i],
                    missed_dates_list[i + 1],
                ]
                break

        # Format the dates as strings
        missed_dates_str = [date.strftime("%Y-%m-%d") for date in missed_dates_list]
        consecutive_missed_days_str = [
            date.strftime("%Y-%m-%d") for date in consecutive_missed_days
        ]

        # Determine the reason
        reason = {}
        if consecutive_missed_days:
            reason["failure_type"] = "consecutive_days_missed"
            reason["consecutive_missed_days"] = consecutive_missed_days_str
        elif len(missed_dates) >= 2:
            reason["failure_type"] = "multiple_days_missed"
        else:
            reason["failure_type"] = "unknown"

        reason["missed_dates"] = missed_dates_str

        return reason

    def reset_stats(self):
        """
        Reset the super challenge stats but keep completion history
        """
        self.current_streak = 0
        self.started_at = timezone.now()
        self.save()

    def check_and_award_if_eligible(self):
        """
        Check if user has achieved 30-day streak and give award if eligible
        """
        if self.highest_streak >= 30 and not self.has_award:
            # Create award for the user
            challenge_award, created = SuperChallengeAward.objects.get_or_create(
                super_challenge=self.super_challenge
            )
            UserSuperAward.objects.get_or_create(
                user=self.user, super_challenge_award=challenge_award
            )
            self.has_award = True
            self.save()
            return True
        return False

    def is_completed_today(self):
        """
        Check if all challenges in the super challenge were completed today
        """
        today = timezone.now().date()
        return self.is_completed_for_date(today)

    def is_completed_for_date(self, check_date):
        """
        Check if all challenges in the super challenge were completed on the specified date

        Args:
            check_date (date): The date to check completions for

        Returns:
            bool: True if all challenges were completed on the specified date, False otherwise
        """
        # Get all challenges in this super challenge
        challenges = self.super_challenge.challenges.all()

        # For each challenge, check if it was completed on the specified date
        for challenge in challenges:
            # Get the user challenge for this challenge
            user_challenge = UserChallenge.objects.filter(
                user=self.user, challenge=challenge, is_active=True
            ).first()

            # If user challenge doesn't exist or wasn't completed on the specified date, return False
            if not user_challenge:
                return False

            # Check if this challenge was completed on the specified date
            completed_on_date = UserChallengeCompletion.objects.filter(
                user_challenge=user_challenge,
                completed_at__date=check_date,
                is_active=True,
            ).exists()

            if not completed_on_date:
                return False

        # If we get here, all challenges were completed on the specified date
        return True

    def update_streak(self, completion_date):
        """
        Update the streak for this super challenge based on completions of all included challenges
        """
        # If super challenge has failed, don't update streak
        if self.is_failed:
            return

        # Check if the super challenge has ended
        today = timezone.now().date()
        if self.super_challenge.end_date < today:
            return

        # Get all completions for this user super challenge
        completions = self.completions.filter(is_active=True)

        # Extract unique dates from completions
        completion_dates = {
            completion.completed_at.date() for completion in completions
        }

        # Filter out any future dates (should not happen, but just in case)
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
        highest_streak = max(streak_lengths) if streak_lengths else 1

        # If there's only one completion, the highest streak is 1
        if len(completion_dates) == 1:
            highest_streak = 1

        # Update highest streak if the new one is higher
        if highest_streak > self.highest_streak:
            self.highest_streak = highest_streak

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

        self.save()

    def check_and_create_completion(self):
        """
        Check if all challenges in the super challenge were completed today,
        and if so, create a completion record
        """
        # If already marked as failed, don't create completions
        if self.is_failed:
            return None

        # Check if the super challenge has ended
        today = timezone.now().date()
        if self.super_challenge.end_date < today:
            return None

        # Check if the super challenge has started
        if self.super_challenge.start_date > today:
            return None

        if self.is_completed_today():
            # Create a completion record for today
            today = timezone.now()

            # Check if we already have a completion for today
            existing_completion = UserSuperChallengeCompletion.objects.filter(
                user_super_challenge=self,
                completed_at__date=today.date(),
                is_active=True,
            ).first()

            if not existing_completion:
                # Create a new completion
                completion = UserSuperChallengeCompletion.objects.create(
                    user_super_challenge=self, completed_at=today
                )

                # Update the streak
                self.update_streak(today.date())

                return completion

            return existing_completion

        return None

    def calculate_streak_before_failure(self):
        """
        Calculate the streak information for a failed challenge.
        This method is used to properly update streak information when a challenge is marked as failed.
        """
        # Get all completions for this user super challenge
        completions = self.completions.filter(is_active=True).order_by(
            "completed_at__date"
        )

        # Extract unique dates from completions
        completion_dates = {
            completion.completed_at.date() for completion in completions
        }

        # If no completions, reset all streak information
        if not completion_dates:
            self.current_streak = 0
            self.highest_streak = 0
            self.total_completions = 0
            self.last_completion_date = None
            self.save()
            return

        # Convert to list and sort
        completion_dates = sorted(list(completion_dates))

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
        highest_streak = max(streak_lengths) if streak_lengths else 1

        # If there's only one completion, the highest streak is 1
        if len(completion_dates) == 1:
            highest_streak = 1

        # Update highest streak
        self.highest_streak = highest_streak

        # Set current streak to 0 since the challenge has failed
        self.current_streak = 0

        # Update last completion date
        self.last_completion_date = completion_dates[-1]

        # Update total completions based on the number of unique completion dates
        self.total_completions = len(completion_dates)

        self.save()


class UserSuperChallengeCompletion(BaseModel):
    """
    Records a completion of all challenges in a super challenge on a specific day.
    """

    user_super_challenge = models.ForeignKey(
        UserSuperChallenge,
        on_delete=models.CASCADE,
        related_name="completions",
        verbose_name=_("User super challenge"),
    )
    completed_at = models.DateTimeField(_("Completed at"))
    is_active = models.BooleanField(_("Is Active"), default=True)

    def save(self, *args, **kwargs):
        if not self.completed_at:
            self.completed_at = timezone.localtime()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-completed_at"]
        verbose_name = _("User Super Challenge Completion")
        verbose_name_plural = _("User Super Challenge Completions")


class SuperChallengeAward(BaseModel):
    """
    Award for completing a super challenge with a 30-day streak.
    """

    super_challenge = models.OneToOneField(
        SuperChallenge,
        on_delete=models.CASCADE,
        related_name="award",
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Award for {self.super_challenge.title}"


class UserSuperAward(BaseModel):
    """
    Records that a user has received an award for a super challenge.
    """

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="super_awards"
    )
    super_challenge_award = models.ForeignKey(
        SuperChallengeAward,
        on_delete=models.CASCADE,
        related_name="user_awards",
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = [("user", "super_challenge_award")]

    def __str__(self):
        return f"{self.user.first_name} - {self.super_challenge_award.super_challenge.title} Award"
