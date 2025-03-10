from django.utils import timezone
from rest_framework import serializers

from apps.main.models import (
    Challenge,
    ChallengeAward,
    SuperChallenge,
    SuperChallengeAward,
    UserChallenge,
    UserChallengeCompletion,
    UserSuperChallenge,
    UserSuperChallengeCompletion,
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
                timezone.localtime(completion.completed_at).date().isoformat()
                for completion in obj._prefetched_completions
            ]

        # Fallback to database query if prefetch didn't happen
        completions = UserChallengeCompletion.objects.filter(
            user_challenge=obj,
            completed_at__year=year,
            completed_at__month=month,
        ).values_list("completed_at", flat=True)

        return [
            timezone.localtime(completion).date().isoformat()
            for completion in completions
        ]


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


class UserChallengeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserChallenge
        fields = ("challenge",)

    def create(self, validated_data):
        user = self.context["request"].user
        challenge = validated_data["challenge"]

        # Check if a user challenge already exists (active or inactive)
        user_challenge = UserChallenge.objects.filter(
            user=user, challenge=challenge
        ).first()

        if user_challenge:
            # If it exists but is inactive, reactivate it
            if not user_challenge.is_active:
                user_challenge.reactivate()
                # Set a flag to indicate this was reactivated
                user_challenge._reactivated = True
            else:
                # If it's already active, just mark it as reactivated for status code purposes
                user_challenge._reactivated = True
            # Return the challenge
            return user_challenge
        else:
            # Create a new user challenge
            user_challenge = UserChallenge.objects.create(
                user=user, challenge=challenge
            )
            # Set flag to indicate this is a new challenge
            user_challenge._reactivated = False

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


class UserChallengeDetailSerializer(UserChallengeListSerializer):
    is_completed_today = serializers.SerializerMethodField()

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
            "is_completed_today",
        )

    def get_is_completed_today(self, obj):
        today = timezone.now().date()
        return UserChallengeCompletion.objects.filter(
            user_challenge=obj, completed_at__date=today
        ).exists()


class SuperChallengeListSerializer(serializers.ModelSerializer):
    challenges_count = serializers.SerializerMethodField()

    class Meta:
        model = SuperChallenge
        fields = (
            "id",
            "title",
            "description",
            "icon",
            "start_date",
            "end_date",
            "challenges_count",
            "created_at",
        )

    def get_challenges_count(self, obj):
        return obj.challenges.count()


class SuperChallengeDetailSerializer(SuperChallengeListSerializer):
    challenges = ChallengeListSerializer(many=True, read_only=True)

    class Meta:
        model = SuperChallenge
        fields = (
            "id",
            "title",
            "description",
            "icon",
            "start_date",
            "end_date",
            "challenges",
            "challenges_count",
            "created_at",
        )


class UserSuperChallengeListSerializer(serializers.ModelSerializer):
    super_challenge = SuperChallengeListSerializer()
    is_completed_today = serializers.SerializerMethodField()

    class Meta:
        model = UserSuperChallenge
        fields = (
            "id",
            "super_challenge",
            "current_streak",
            "highest_streak",
            "total_completions",
            "last_completion_date",
            "is_completed_today",
            "is_failed",
            "created_at",
        )

    def get_is_completed_today(self, obj):
        return obj.is_completed_today()


class UserSuperChallengeDetailSerializer(UserSuperChallengeListSerializer):
    super_challenge = SuperChallengeDetailSerializer()
    included_challenges_status = serializers.SerializerMethodField()

    class Meta:
        model = UserSuperChallenge
        fields = (
            "id",
            "super_challenge",
            "current_streak",
            "highest_streak",
            "total_completions",
            "last_completion_date",
            "is_completed_today",
            "is_failed",
            "included_challenges_status",
            "created_at",
        )

    def get_included_challenges_status(self, obj):
        """
        Return the status of each challenge in the super challenge
        """
        today = timezone.now().date()
        result = []

        for challenge in obj.super_challenge.challenges.all():
            # Get the user challenge for this challenge
            user_challenge = UserChallenge.objects.filter(
                user=obj.user, challenge=challenge, is_active=True
            ).first()

            status = {
                "challenge_id": challenge.id,
                "challenge_title": challenge.title,
                "is_active": bool(user_challenge),
                "is_completed_today": False,
                "current_streak": 0,
                "highest_streak": 0,
            }

            if user_challenge:
                # Check if this challenge was completed today
                completed_today = UserChallengeCompletion.objects.filter(
                    user_challenge=user_challenge,
                    completed_at__date=today,
                    is_active=True,
                ).exists()

                status.update(
                    {
                        "is_completed_today": completed_today,
                        "current_streak": user_challenge.current_streak,
                        "highest_streak": user_challenge.highest_streak,
                    }
                )

            result.append(status)

        return result


class SuperChallengeCalendarSerializer(serializers.ModelSerializer):
    completion_dates = serializers.SerializerMethodField()
    calendar_icon = serializers.SerializerMethodField()
    title = serializers.CharField(source="super_challenge.title")

    class Meta:
        model = UserSuperChallenge
        fields = (
            "id",
            "title",
            "calendar_icon",
            "completion_dates",
            "current_streak",
            "highest_streak",
            "total_completions",
        )

    def get_calendar_icon(self, obj):
        request = self.context.get("request")
        if obj.super_challenge.calendar_icon:
            return request.build_absolute_uri(obj.super_challenge.calendar_icon.url)
        return None

    def get_completion_dates(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []

        month = self.context.get("month", timezone.now().month)
        year = self.context.get("year", timezone.now().year)

        # Use prefetched data if available
        if hasattr(obj, "_prefetched_completions"):
            return [
                timezone.localtime(completion.completed_at).date().isoformat()
                for completion in obj._prefetched_completions
            ]

        # Fallback to database query if prefetch didn't happen
        completions = UserSuperChallengeCompletion.objects.filter(
            user_super_challenge=obj,
            completed_at__year=year,
            completed_at__month=month,
        ).values_list("completed_at", flat=True)

        return [
            timezone.localtime(completion).date().isoformat()
            for completion in completions
        ]


class AllSuperChallengesCalendarSerializer(serializers.Serializer):
    calendar_data = serializers.SerializerMethodField()

    def get_calendar_data(self, obj):
        request = self.context.get("request")
        month = self.context.get("month")
        year = self.context.get("year")

        user_super_challenges = obj.get("user_super_challenges", [])

        result = []
        for user_super_challenge in user_super_challenges:
            serializer = SuperChallengeCalendarSerializer(
                user_super_challenge,
                context={"request": request, "month": month, "year": year},
            )
            result.append(serializer.data)

        return result


class SuperChallengeAwardSerializer(serializers.ModelSerializer):
    super_challenge_title = serializers.CharField(
        source="super_challenge.title", read_only=True
    )
    award_icon = serializers.SerializerMethodField()
    is_user_awarded = serializers.SerializerMethodField()

    class Meta:
        model = SuperChallengeAward
        fields = (
            "id",
            "super_challenge_title",
            "award_icon",
            "is_user_awarded",
            "created_at",
        )

    def get_award_icon(self, obj):
        request = self.context.get("request")
        if obj.super_challenge.award_icon:
            return request.build_absolute_uri(obj.super_challenge.award_icon.url)
        return None

    def get_is_user_awarded(self, obj):
        return bool(getattr(obj, "_prefetched_user_awards", []))
