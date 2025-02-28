from django.contrib import admin

from apps.main.models import Challenge, UserChallenge, UserChallengeCompletion


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "start_time", "end_time")
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
    list_display = ("user_challenge", "completed_at")
    list_filter = ("completed_at",)
