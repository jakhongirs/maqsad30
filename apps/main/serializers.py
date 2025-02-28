from django.utils import timezone
from rest_framework import serializers

from apps.main.models import Challenge, UserChallenge, UserChallengeCompletion


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
            "start_time",
            "end_time",
            "created_at",
            "updated_at",
            "current_streak",
        )


class ChallengeDetailSerializer(serializers.ModelSerializer):
    total_completions = serializers.SerializerMethodField()

    def get_total_completions(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0

        user_challenge = UserChallenge.objects.filter(
            user=request.user, challenge=obj
        ).first()

        return user_challenge.total_completions if user_challenge else 0

    class Meta:
        model = Challenge
        fields = (
            "id",
            "title",
            "icon",
            "video_instruction_url",
            "start_time",
            "end_time",
            "created_at",
            "updated_at",
            "total_completions",
        )


class UserChallengeCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserChallengeCompletion
        fields = ("id", "completed_at")
        read_only_fields = ("id", "completed_at")


class ChallengeCalendarSerializer(serializers.ModelSerializer):
    completion_dates = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = (
            "id",
            "title",
            "completion_dates",
        )

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
                date_str = completion_date.strftime("%d.%m.%Y")

                if date_str not in dates_dict:
                    dates_dict[date_str] = {"date": date_str, "challenges": []}

                dates_dict[date_str]["challenges"].append(
                    {
                        "title": user_challenge.challenge.title,
                        "icon": request.build_absolute_uri(
                            user_challenge.challenge.icon.url
                        )
                        if user_challenge.challenge.icon
                        else None,
                    }
                )

        # Convert dictionary to sorted list
        result = sorted(dates_dict.values(), key=lambda x: x["date"], reverse=True)
        return result
