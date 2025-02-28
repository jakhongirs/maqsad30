from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel

User = get_user_model()


class Challenge(BaseModel):
    title = models.CharField(max_length=255)
    icon = models.ImageField(upload_to="challenge_icons/")
    video_instruction_url = models.URLField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-created_at"]


class UserChallenge(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_challenges"
    )
    challenge = models.ForeignKey(
        Challenge, on_delete=models.CASCADE, related_name="user_challenges"
    )
    current_streak = models.PositiveIntegerField(default=0)
    highest_streak = models.PositiveIntegerField(default=0)
    total_completions = models.PositiveIntegerField(default=0)
    last_completion_date = models.DateField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "challenge"]
        ordering = ["-current_streak", "-highest_streak"]

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


class ChallengeCompletion(BaseModel):
    user_challenge = models.ForeignKey(
        UserChallenge, on_delete=models.CASCADE, related_name="completions"
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]


class ChallengeAward(BaseModel):
    user_challenge = models.OneToOneField(
        UserChallenge, on_delete=models.CASCADE, related_name="award"
    )
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-awarded_at"]
