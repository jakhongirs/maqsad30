from typing import Any

from django.contrib import admin

from apps.main.models import (
    Challenge,
    ChallengeAward,
    SuperChallenge,
    SuperChallengeAward,
    UserAward,
    UserChallenge,
    UserChallengeCompletion,
    UserSuperAward,
    UserSuperChallenge,
    UserSuperChallengeCompletion,
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
        "is_active",
    )
    list_filter = ("challenge", "last_completion_date", "is_active")
    search_fields = ("user__username", "challenge__title")


@admin.register(UserChallengeCompletion)
class UserChallengeCompletionAdmin(admin.ModelAdmin):
    list_display = (
        "user_challenge",
        "get_user_first_name",
        "get_user_telegram_id",
        "get_challenge_title",
        "completed_at",
        "is_active",
    )
    list_filter = ("completed_at", "is_active")
    search_fields = (
        "user_challenge__user__first_name",
        "user_challenge__user__telegram_id",
    )

    def get_user_first_name(self, obj: Any) -> str:
        return obj.user_challenge.user.first_name

    get_user_first_name.short_description = "User First Name"  # type: ignore
    get_user_first_name.admin_order_field = "user_challenge__user__first_name"  # type: ignore

    def get_user_telegram_id(self, obj: Any) -> str:
        return obj.user_challenge.user.telegram_id

    get_user_telegram_id.short_description = "User Telegram ID"  # type: ignore
    get_user_telegram_id.admin_order_field = "user_challenge__user__telegram_id"  # type: ignore

    def get_challenge_title(self, obj: Any) -> str:
        return obj.user_challenge.challenge.title

    get_challenge_title.short_description = "Challenge Title"  # type: ignore
    get_challenge_title.admin_order_field = "user_challenge__challenge__title"  # type: ignore


@admin.register(ChallengeAward)
class ChallengeAwardAdmin(admin.ModelAdmin):
    list_display = ("challenge", "created_at")
    list_filter = ("created_at",)
    search_fields = ("challenge__title",)


@admin.register(UserAward)
class UserAwardAdmin(admin.ModelAdmin):
    list_display = ("user", "challenge_award", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "challenge_award__challenge__title")


# Super Challenge Admin Models
@admin.register(SuperChallenge)
class SuperChallengeAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "start_date",
        "end_date",
        "get_challenges_count",
        "created_at",
    )
    list_filter = ("start_date", "end_date")
    search_fields = ("title",)
    filter_horizontal = ("challenges",)

    def get_challenges_count(self, obj: Any) -> int:
        return obj.challenges.count()

    get_challenges_count.short_description = "Challenges Count"  # type: ignore


@admin.register(UserSuperChallenge)
class UserSuperChallengeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "super_challenge",
        "current_streak",
        "highest_streak",
        "total_completions",
        "last_completion_date",
        "started_at",
        "is_active",
        "is_failed",
    )
    list_filter = ("super_challenge", "last_completion_date", "is_active", "is_failed")
    search_fields = ("user__username", "super_challenge__title")


@admin.register(UserSuperChallengeCompletion)
class UserSuperChallengeCompletionAdmin(admin.ModelAdmin):
    list_display = (
        "user_super_challenge",
        "get_user_first_name",
        "get_user_telegram_id",
        "get_super_challenge_title",
        "completed_at",
        "is_active",
    )
    list_filter = ("completed_at", "is_active")
    search_fields = (
        "user_super_challenge__user__first_name",
        "user_super_challenge__user__telegram_id",
    )

    def get_user_first_name(self, obj: Any) -> str:
        return obj.user_super_challenge.user.first_name

    get_user_first_name.short_description = "User First Name"  # type: ignore
    get_user_first_name.admin_order_field = "user_super_challenge__user__first_name"  # type: ignore

    def get_user_telegram_id(self, obj: Any) -> str:
        return obj.user_super_challenge.user.telegram_id

    get_user_telegram_id.short_description = "User Telegram ID"  # type: ignore
    get_user_telegram_id.admin_order_field = "user_super_challenge__user__telegram_id"  # type: ignore

    def get_super_challenge_title(self, obj: Any) -> str:
        return obj.user_super_challenge.super_challenge.title

    get_super_challenge_title.short_description = "Super Challenge Title"  # type: ignore
    get_super_challenge_title.admin_order_field = (  # type: ignore
        "user_super_challenge__super_challenge__title"
    )


@admin.register(SuperChallengeAward)
class SuperChallengeAwardAdmin(admin.ModelAdmin):
    list_display = ("super_challenge", "created_at")
    list_filter = ("created_at",)
    search_fields = ("super_challenge__title",)


@admin.register(UserSuperAward)
class UserSuperAwardAdmin(admin.ModelAdmin):
    list_display = ("user", "super_challenge_award", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "super_challenge_award__super_challenge__title")
