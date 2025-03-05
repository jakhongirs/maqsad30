from django.utils import timezone
from rest_framework import serializers

from apps.main.models import (
    Challenge,
    ChallengeAward,
    Tournament,
    UserChallenge,
    UserChallengeCompletion,
)


class ChallengeListSerializer(serializers.ModelSerializer):
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
            "rules",
        )


class UserChallengeCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserChallengeCompletion
        fields = ("id", "completed_at")
        read_only_fields = ("id", "completed_at")


class ChallengeCalendarSerializer(serializers.ModelSerializer):
    completion_dates = serializers.SerializerMethodField()
    calendar_icon = serializers.SerializerMethodField()
    title = serializers.CharField(source="challenge.title")

    class Meta:
        model = UserChallenge
        fields = (
            "id",
            "title",
            "calendar_icon",
            "completion_dates",
        )

    def get_calendar_icon(self, obj):
        request = self.context.get("request")
        if obj.challenge.calendar_icon:
            return request.build_absolute_uri(obj.challenge.calendar_icon.url)
        return (
            request.build_absolute_uri(obj.challenge.icon.url)
            if obj.challenge.icon
            else None
        )

    def get_completion_dates(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []

        month = self.context.get("month", timezone.now().month)
        year = self.context.get("year", timezone.now().year)

        # Use prefetched data if available
        if hasattr(obj, "_prefetched_completions"):
            return [
                completion.completed_at.date().isoformat()
                for completion in obj._prefetched_completions
            ]

        # Fallback to database query if prefetch didn't happen
        completion_dates = UserChallengeCompletion.objects.filter(
            user_challenge=obj,
            completed_at__year=year,
            completed_at__month=month,
        ).dates("completed_at", "day")

        return [date.isoformat() for date in completion_dates]


class AllChallengesCalendarSerializer(serializers.Serializer):
    calendar_data = serializers.SerializerMethodField()

    def get_calendar_data(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []

        user_challenges = obj.get("user_challenges", [])
        dates_dict = {}

        # Process all completions from prefetched data
        for user_challenge in user_challenges:
            challenge = user_challenge.challenge
            icon_url = None
            if challenge.calendar_icon:
                icon_url = request.build_absolute_uri(challenge.calendar_icon.url)
            elif challenge.icon:
                icon_url = request.build_absolute_uri(challenge.icon.url)

            challenge_info = {
                "title": challenge.title,
                "calendar_icon": icon_url,
            }

            # Use prefetched completions
            if hasattr(user_challenge, "_prefetched_completions"):
                for completion in user_challenge._prefetched_completions:
                    date_str = completion.completed_at.date().isoformat()
                    if date_str not in dates_dict:
                        dates_dict[date_str] = {"date": date_str, "challenges": []}
                    dates_dict[date_str]["challenges"].append(challenge_info)

        # Convert dictionary to sorted list
        result = sorted(dates_dict.values(), key=lambda x: x["date"], reverse=True)
        return result


class ChallengeLeaderboardSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    highest_streak = serializers.IntegerField()

    class Meta:
        model = UserChallenge
        fields = (
            "user",
            "highest_streak",
        )

    def get_user(self, obj):
        request = self.context.get("request")
        user = obj.user
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
        return bool(getattr(obj, "_prefetched_user_awards", []))


class TournamentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournament
        fields = (
            "id",
            "title",
            "icon",
            "finish_date",
            "is_active",
            "created_at",
            "updated_at",
        )


class TournamentChallengeSerializer(serializers.ModelSerializer):
    current_streak = serializers.SerializerMethodField()

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
            "rules",
            "current_streak",
        )

    def get_current_streak(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0

        # Use prefetched data if available
        if hasattr(obj, "_prefetched_user_challenges"):
            user_challenges = obj._prefetched_user_challenges
            return user_challenges[0].current_streak if user_challenges else 0

        # Fallback to database query if prefetch didn't happen
        user_challenge = UserChallenge.objects.filter(
            user=request.user, challenge=obj
        ).first()

        return user_challenge.current_streak if user_challenge else 0


class TournamentDetailSerializer(serializers.ModelSerializer):
    challenges = TournamentChallengeSerializer(many=True, read_only=True)

    class Meta:
        model = Tournament
        fields = (
            "id",
            "title",
            "icon",
            "finish_date",
            "is_active",
            "challenges",
            "created_at",
            "updated_at",
        )


class UserChallengeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserChallenge
        fields = ("challenge",)

    def create(self, validated_data):
        user = self.context["request"].user
        challenge = validated_data["challenge"]

        user_challenge, created = UserChallenge.objects.get_or_create(
            user=user, challenge=challenge
        )

        return user_challenge


class UserChallengeListSerializer(serializers.ModelSerializer):
    challenge = ChallengeListSerializer()

    class Meta:
        model = UserChallenge
        fields = (
            "id",
            "challenge",
            "current_streak",
            "highest_streak",
            "total_completions",
            "last_completion_date",
            "started_at",
        )
