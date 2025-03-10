from django.utils import timezone
from rest_framework import serializers

from apps.main.models import (
    Challenge,
    ChallengeAward,
    Tournament,
    UserChallenge,
    UserChallengeCompletion,
    UserTournament,
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


class TournamentChallengeListSerializer(serializers.ModelSerializer):
    current_streak = serializers.SerializerMethodField()
    user_challenge_id = serializers.SerializerMethodField()
    total_completions = serializers.SerializerMethodField()
    is_completed_today = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = (
            "id",
            "title",
            "icon",
            "calendar_icon",
            "award_icon",
            "video_instruction_url",
            "video_instruction_title",
            "rules",
            "start_time",
            "end_time",
            "created_at",
            "current_streak",
            "user_challenge_id",
            "total_completions",
            "is_completed_today",
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

    def get_user_challenge_id(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        # Use prefetched data if available
        if hasattr(obj, "_prefetched_user_challenges"):
            user_challenges = obj._prefetched_user_challenges
            return user_challenges[0].id if user_challenges else None

        # Fallback to database query if prefetch didn't happen
        user_challenge = UserChallenge.objects.filter(
            user=request.user, challenge=obj
        ).first()

        return user_challenge.id if user_challenge else None

    def get_total_completions(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0

        # Use prefetched data if available
        if hasattr(obj, "_prefetched_user_challenges"):
            user_challenges = obj._prefetched_user_challenges
            return user_challenges[0].total_completions if user_challenges else 0

        # Fallback to database query if prefetch didn't happen
        user_challenge = UserChallenge.objects.filter(
            user=request.user, challenge=obj
        ).first()

        return user_challenge.total_completions if user_challenge else 0

    def get_is_completed_today(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        today = timezone.now().date()

        # Use prefetched data if available
        if hasattr(obj, "_prefetched_user_challenges"):
            user_challenges = obj._prefetched_user_challenges
            if not user_challenges:
                return False

            user_challenge = user_challenges[0]
            if hasattr(user_challenge, "_prefetched_completions_today"):
                return bool(user_challenge._prefetched_completions_today)

        # Fallback to database query if prefetch didn't happen
        return UserChallengeCompletion.objects.filter(
            user_challenge__user=request.user,
            user_challenge__challenge=obj,
            completed_at__date=today,
        ).exists()


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


class TournamentListSerializer(serializers.ModelSerializer):
    challenges = TournamentChallengeListSerializer(many=True, read_only=True)

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
            "challenges",
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


class UserTournamentSerializer(serializers.ModelSerializer):
    tournament = TournamentListSerializer()

    class Meta:
        model = UserTournament
        fields = (
            "id",
            "tournament",
            "consecutive_failures",
            "total_failures",
            "is_failed",
            "started_at",
        )


class TournamentDetailSerializer(serializers.ModelSerializer):
    challenges = TournamentChallengeListSerializer(many=True, read_only=True)

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
            "challenges",
        )


class TournamentCalendarSerializer(serializers.ModelSerializer):
    calendar_data = serializers.SerializerMethodField()
    calendar_icon = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = (
            "id",
            "title",
            "icon",
            "calendar_icon",
            "award_icon",
            "start_date",
            "finish_date",
            "calendar_data",
        )

    def get_calendar_icon(self, obj):
        request = self.context.get("request")
        if obj.calendar_icon:
            return request.build_absolute_uri(obj.calendar_icon.url)
        return None

    def get_calendar_data(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []

        month = self.context.get("month")
        year = self.context.get("year")

        # Get user tournament
        user_tournament = obj.user_tournaments.filter(user=request.user).first()
        if not user_tournament:
            return []

        # Get all daily records for the specified month
        daily_records = user_tournament.daily_records.filter(
            date__year=year, date__month=month
        ).prefetch_related("completed_challenges")

        calendar_data = []
        for record in daily_records:
            calendar_data.append(
                {
                    "date": record.date,
                    "is_completed": record.is_completed,
                    "completed_challenges": [
                        {
                            "id": challenge.id,
                            "title": challenge.title,
                            "icon": request.build_absolute_uri(challenge.icon.url)
                            if challenge.icon
                            else None,
                            "calendar_icon": request.build_absolute_uri(
                                challenge.calendar_icon.url
                            )
                            if challenge.calendar_icon
                            else None,
                        }
                        for challenge in record.completed_challenges.all()
                    ],
                }
            )

        return calendar_data


class TournamentChallengeCalendarSerializer(serializers.ModelSerializer):
    calendar_data = serializers.SerializerMethodField()
    calendar_icon = serializers.SerializerMethodField()
    challenge = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = (
            "id",
            "title",
            "icon",
            "calendar_icon",
            "award_icon",
            "start_date",
            "finish_date",
            "challenge",
            "calendar_data",
        )

    def get_calendar_icon(self, obj):
        request = self.context.get("request")
        if obj.calendar_icon:
            return request.build_absolute_uri(obj.calendar_icon.url)
        return None

    def get_challenge(self, obj):
        challenge = self.context.get("challenge")
        request = self.context.get("request")
        if not challenge:
            return None

        return {
            "id": challenge.id,
            "title": challenge.title,
            "icon": request.build_absolute_uri(challenge.icon.url)
            if challenge.icon
            else None,
            "calendar_icon": request.build_absolute_uri(challenge.calendar_icon.url)
            if challenge.calendar_icon
            else None,
        }

    def get_calendar_data(self, obj):
        request = self.context.get("request")
        challenge = self.context.get("challenge")
        if not request or not request.user.is_authenticated or not challenge:
            return []

        month = self.context.get("month")
        year = self.context.get("year")

        # Get user tournament
        user_tournament = obj.user_tournaments.filter(user=request.user).first()
        if not user_tournament:
            return []

        # Get all daily records for the specified month
        daily_records = user_tournament.daily_records.filter(
            date__year=year, date__month=month
        ).prefetch_related("completed_challenges")

        calendar_data = []
        for record in daily_records:
            # Check if the specific challenge was completed on this day
            if challenge in record.completed_challenges.all():
                calendar_data.append({"date": record.date, "is_completed": True})

        return calendar_data


class TournamentLeaderboardSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    completed_days = serializers.SerializerMethodField()

    class Meta:
        model = UserTournament
        fields = (
            "user",
            "completed_days",
            "is_failed",
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

    def get_completed_days(self, obj):
        return obj.daily_records.filter(is_completed=True).count()
