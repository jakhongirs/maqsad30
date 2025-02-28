from django.contrib.auth import get_user_model
from django.db import models

from apps.common.models import BaseModel

User = get_user_model()


class Question(BaseModel):
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class Answer(BaseModel):
    question = models.ForeignKey(
        Question, related_name="answers", on_delete=models.CASCADE
    )
    text = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.question.title} - {self.text}"


class UserAnswer(BaseModel):
    user = models.ForeignKey(
        User, related_name="onboarding_answers", on_delete=models.CASCADE
    )
    question = models.ForeignKey(
        Question, related_name="user_answers", on_delete=models.CASCADE
    )
    answer = models.ForeignKey(
        Answer, related_name="user_selections", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ["user", "question"]

    def __str__(self):
        return f"{self.user.username} - {self.question.title}"
