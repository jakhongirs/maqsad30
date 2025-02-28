from django.contrib import admin

from .models import Answer, Question, UserAnswer


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["title", "order", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["title"]
    ordering = ["order"]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ["text", "question", "order", "is_active"]
    list_filter = ["question", "is_active"]
    search_fields = ["text", "question__title"]
    ordering = ["question", "order"]


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ["user", "question", "answer", "created_at"]
    list_filter = ["question", "created_at"]
    search_fields = ["user__username", "question__title", "answer__text"]
    raw_id_fields = ["user", "question", "answer"]
