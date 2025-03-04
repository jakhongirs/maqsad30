from django.contrib import admin

from apps.main.models import (
    Challenge,
    ChallengeAward,
    Tournament,
    UserAward,
    UserChallenge,
    UserChallengeCompletion,
)


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "start_time", "end_time", "created_at")
    list_filter = ("start_time", "end_time")
    search_fields = ("title",)


@admin.register(UserChallenge)
class UserChallengeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "challenge",
        "current_streak",
        "highest_streak",
        "total_completions",
        "last_completion_date",
    )
    list_filter = ("challenge", "last_completion_date")
    search_fields = ("user__username", "challenge__title")


@admin.register(UserChallengeCompletion)
class UserChallengeCompletionAdmin(admin.ModelAdmin):
    list_display = (
        "user_challenge",
        "user_challenge__user__first_name",
        "user_challenge__user__telegram_id",
        "user_challenge__challenge__title",
        "completed_at",
    )
    list_filter = ("completed_at",)
    search_fields = (
        "user_challenge__user__first_name",
        "user_challenge__user__telegram_id",
    )


@admin.register(ChallengeAward)
class ChallengeAwardAdmin(admin.ModelAdmin):
    list_display = ("challenge", "created_at")
    list_filter = ("created_at",)
    search_fields = ("challenge__title",)


@admin.register(UserAward)
class UserAwardAdmin(admin.ModelAdmin):
    list_display = ("user", "award", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "award__challenge__title")


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("title", "finish_date", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title",)
