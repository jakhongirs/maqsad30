from django.utils import timezone
from rest_framework import serializers

from apps.main.models import (
    Challenge,
    ChallengeAward,
    UserAward,
    UserChallenge,
    UserChallengeCompletion,
)


class ChallengeListSerializer(serializers.ModelSerializer):
    current_streak = serializers.SerializerMethodField()

    def get_current_streak(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0

        user_challenge = UserChallenge.objects.filter(
            user=request.user, challenge=obj
        ).first()

        return user_challenge.current_streak if user_challenge else 0

    class Meta:
        model = Challenge
        fields = (
            "id",
            "title",
            "icon",
            "video_instruction_url",
            "video_instruction_title",
            "start_time",
            "end_time",
            "created_at",
            "updated_at",
            "current_streak",
        )


class ChallengeDetailSerializer(serializers.ModelSerializer):
    total_completions = serializers.SerializerMethodField()
    is_completed_today = serializers.SerializerMethodField()

    def get_total_completions(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0

        user_challenge = UserChallenge.objects.filter(
            user=request.user, challenge=obj
        ).first()

        return user_challenge.total_completions if user_challenge else 0

    def get_is_completed_today(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        today = timezone.now().date()
        user_challenge = UserChallenge.objects.filter(
            user=request.user, challenge=obj, last_completion_date=today
        ).exists()

        return user_challenge

    class Meta:
        model = Challenge
        fields = (
            "id",
            "title",
            "icon",
            "video_instruction_url",
            "video_instruction_title",
            "start_time",
            "end_time",
            "created_at",
            "updated_at",
            "total_completions",
            "is_completed_today",
        )


class UserChallengeCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserChallengeCompletion
        fields = ("id", "completed_at")
        read_only_fields = ("id", "completed_at")


class ChallengeCalendarSerializer(serializers.ModelSerializer):
    completion_dates = serializers.SerializerMethodField()
    calendar_icon = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = (
            "id",
            "title",
            "calendar_icon",
            "completion_dates",
        )

    def get_calendar_icon(self, obj):
        request = self.context.get("request")
        if obj.calendar_icon:
            return request.build_absolute_uri(obj.calendar_icon.url)
        return request.build_absolute_uri(obj.icon.url) if obj.icon else None

    def get_completion_dates(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []

        user_challenge = UserChallenge.objects.filter(
            user=request.user, challenge=obj
        ).first()

        if not user_challenge:
            return []

        # Get month from query params or use current month
        month = self.context.get("month", timezone.now().month)
        year = self.context.get("year", timezone.now().year)

        # Get all completion dates for the challenge filtered by month
        completion_dates = UserChallengeCompletion.objects.filter(
            user_challenge=user_challenge,
            completed_at__year=year,
            completed_at__month=month,
        ).dates("completed_at", "day")

        return [date.isoformat() for date in completion_dates]


class AllChallengesCalendarSerializer(serializers.ModelSerializer):
    calendar_data = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = ("calendar_data",)

    def get_calendar_data(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []

        # Get month from query params or use current month
        month = self.context.get("month", timezone.now().month)
        year = self.context.get("year", timezone.now().year)

        # Get all user challenges with their completions for the specified month
        user_challenges = UserChallenge.objects.filter(
            user=request.user
        ).select_related("challenge")

        # Dictionary to store challenges by date
        dates_dict = {}

        for user_challenge in user_challenges:
            # Get completions for this challenge in the specified month
            completions = UserChallengeCompletion.objects.filter(
                user_challenge=user_challenge,
                completed_at__year=year,
                completed_at__month=month,
            ).values_list("completed_at", flat=True)

            # Add challenge to each completion date
            for completion_date in completions:
                date_str = completion_date.date().isoformat()

                if date_str not in dates_dict:
                    dates_dict[date_str] = {"date": date_str, "challenges": []}

                challenge = user_challenge.challenge
                icon_url = None
                if challenge.calendar_icon:
                    icon_url = request.build_absolute_uri(challenge.calendar_icon.url)
                elif challenge.icon:
                    icon_url = request.build_absolute_uri(challenge.icon.url)

                dates_dict[date_str]["challenges"].append(
                    {
                        "title": challenge.title,
                        "calendar_icon": icon_url,
                    }
                )

        # Convert dictionary to sorted list
        result = sorted(dates_dict.values(), key=lambda x: x["date"], reverse=True)
        return result


class ChallengeLeaderboardSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    highest_streak = serializers.IntegerField(source="user_challenges__highest_streak")

    class Meta:
        model = Challenge
        fields = (
            "user",
            "highest_streak",
        )

    def get_user(self, obj):
        request = self.context.get("request")
        user = obj.user_challenges.first().user
        return {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "telegram_username": user.telegram_username,
            "telegram_photo": request.build_absolute_uri(user.telegram_photo.url)
            if user.telegram_photo
            else user.telegram_photo_url,
        }


class Challenge30DaysPlusStreakSerializer(serializers.ModelSerializer):
    leaderboard = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = ("id", "title", "icon", "leaderboard", "created_at")

    def get_leaderboard(self, obj):
        request = self.context.get("request")
        user_challenges = (
            UserChallenge.objects.filter(challenge=obj, highest_streak__gte=30)
            .select_related("user")
            .order_by("-highest_streak")
        )

        return [
            {
                "user": {
                    "id": uc.user.id,
                    "first_name": uc.user.first_name,
                    "last_name": uc.user.last_name,
                    "telegram_username": uc.user.telegram_username,
                    "telegram_photo": request.build_absolute_uri(
                        uc.user.telegram_photo.url
                    )
                    if uc.user.telegram_photo
                    else uc.user.telegram_photo_url,
                },
                "highest_streak": uc.highest_streak,
            }
            for uc in user_challenges
        ]


class ChallengeAwardSerializer(serializers.ModelSerializer):
    challenge_title = serializers.CharField(source="challenge.title", read_only=True)
    award_icon = serializers.SerializerMethodField()
    is_user_awarded = serializers.SerializerMethodField()

    class Meta:
        model = ChallengeAward
        fields = (
            "id",
            "challenge_title",
            "award_icon",
            "is_user_awarded",
            "created_at",
        )

    def get_award_icon(self, obj):
        request = self.context.get("request")
        if obj.challenge.award_icon:
            return request.build_absolute_uri(obj.challenge.award_icon.url)
        return None

    def get_is_user_awarded(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        return UserAward.objects.filter(user=request.user, award=obj).exists()
