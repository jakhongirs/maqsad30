from django.contrib import admin

from apps.main.models import (
    Challenge,
    ChallengeAward,
    Tournament,
    UserAward,
    UserChallenge,
    UserChallengeCompletion,
    UserTournament,
    UserTournamentDay,
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
        "started_at",
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
    list_display = ("user", "get_award_name", "created_at")
    list_filter = ("created_at",)
    search_fields = (
        "user__username",
        "challenge_award__challenge__title",
        "tournament_award__tournament__title",
    )

    def get_award_name(self, obj):
        if obj.challenge_award:
            return f"{obj.challenge_award.challenge.title} Award"
        return f"{obj.tournament_award.tournament.title} Award"


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("title", "start_date", "finish_date", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title",)


@admin.register(UserTournament)
class UserTournamentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "tournament",
        "consecutive_failures",
        "total_failures",
        "is_failed",
        "started_at",
    )
    list_filter = ("is_failed", "started_at")
    search_fields = ("user__username", "tournament__title")


@admin.register(UserTournamentDay)
class UserTournamentDayAdmin(admin.ModelAdmin):
    list_display = ("user_tournament", "date", "is_completed")
    list_filter = ("date", "is_completed")
    search_fields = (
        "user_tournament__user__username",
        "user_tournament__tournament__title",
    )
