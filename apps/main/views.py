from django.db import models
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.main.models import (
    Challenge,
    ChallengeAward,
    Tournament,
    UserAward,
    UserChallenge,
    UserChallengeCompletion,
)
from apps.main.serializers import (
    AllChallengesCalendarSerializer,
    Challenge30DaysPlusStreakSerializer,
    ChallengeAwardSerializer,
    ChallengeCalendarSerializer,
    ChallengeDetailSerializer,
    ChallengeLeaderboardSerializer,
    ChallengeListSerializer,
    TournamentDetailSerializer,
    TournamentListSerializer,
    UserChallengeCompletionSerializer,
)
from apps.users.permissions import IsTelegramUser


class ChallengeListAPIView(ListAPIView):
    serializer_class = ChallengeListSerializer
    permission_classes = [IsTelegramUser]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Challenge.objects.all()

        return Challenge.objects.prefetch_related(
            Prefetch(
                "user_challenges",
                queryset=UserChallenge.objects.filter(user=self.request.user),
                to_attr="_prefetched_user_challenges",
            )
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context


class ChallengeDetailAPIView(RetrieveAPIView):
    serializer_class = ChallengeDetailSerializer
    permission_classes = [IsTelegramUser]
    lookup_field = "id"

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Challenge.objects.all()

        today = timezone.now().date()
        return Challenge.objects.prefetch_related(
            Prefetch(
                "user_challenges",
                queryset=UserChallenge.objects.filter(user=self.request.user),
                to_attr="_prefetched_user_challenges",
            )
        ).annotate(
            is_completed_today=models.Exists(
                UserChallenge.objects.filter(
                    user=self.request.user,
                    challenge=models.OuterRef("pk"),
                    last_completion_date=today,
                )
            )
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context


class UserChallengeCompletionAPIView(CreateAPIView):
    serializer_class = UserChallengeCompletionSerializer
    permission_classes = [IsTelegramUser]

    def perform_create(self, serializer):
        challenge_id = self.kwargs["id"]
        try:
            challenge = Challenge.objects.get(id=challenge_id)
        except Challenge.DoesNotExist:
            raise ValidationError("Challenge not found")

        # Get current time and date in UTC
        now = timezone.now()
        current_time = now.time()
        current_date = now.date()

        # Check if current time is within the challenge time window
        if current_time < challenge.start_time or current_time > challenge.end_time:
            raise ValidationError(
                f"Challenge can only be completed between {challenge.start_time.strftime('%H:%M')} "
                f"and {challenge.end_time.strftime('%H:%M')}"
            )

        # Get or create UserChallenge
        user_challenge, _ = UserChallenge.objects.get_or_create(
            user=self.request.user, challenge=challenge
        )

        # Check if user has already completed the challenge today
        already_completed = UserChallengeCompletion.objects.filter(
            user_challenge=user_challenge, completed_at__date=current_date
        ).exists()

        if already_completed:
            raise ValidationError("You have already completed this challenge today")

        # Create completion
        completion = serializer.save(user_challenge=user_challenge)

        # Update streak
        user_challenge.update_streak(current_date)

        return completion


class ChallengeCalendarAPIView(RetrieveAPIView):
    serializer_class = ChallengeCalendarSerializer
    permission_classes = [IsTelegramUser]
    lookup_field = "id"

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Challenge.objects.all()

        try:
            month = int(self.request.query_params.get("month", timezone.now().month))
            year = int(self.request.query_params.get("year", timezone.now().year))
            if not 1 <= month <= 12:
                raise ValidationError("Month must be between 1 and 12")
        except ValueError:
            raise ValidationError("Invalid month or year format")

        return Challenge.objects.prefetch_related(
            Prefetch(
                "user_challenges",
                queryset=UserChallenge.objects.filter(
                    user=self.request.user
                ).prefetch_related(
                    Prefetch(
                        "completions",
                        queryset=UserChallengeCompletion.objects.filter(
                            completed_at__year=year, completed_at__month=month
                        ),
                        to_attr="_prefetched_completions",
                    )
                ),
                to_attr="_prefetched_user_challenges",
            )
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            month = int(self.request.query_params.get("month", timezone.now().month))
            year = int(self.request.query_params.get("year", timezone.now().year))
            if not 1 <= month <= 12:
                raise ValidationError("Month must be between 1 and 12")
        except ValueError:
            raise ValidationError("Invalid month or year format")

        context["month"] = month
        context["year"] = year
        return context


class AllChallengesCalendarAPIView(APIView):
    permission_classes = [IsTelegramUser]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"calendar_data": []})

        try:
            month = int(request.query_params.get("month", timezone.now().month))
            year = int(request.query_params.get("year", timezone.now().year))
            if not 1 <= month <= 12:
                raise ValidationError("Month must be between 1 and 12")
        except ValueError:
            raise ValidationError("Invalid month or year format")

        # Get all completions for the month in a single query
        user_challenges = (
            UserChallenge.objects.filter(user=request.user)
            .select_related("challenge")
            .prefetch_related(
                Prefetch(
                    "completions",
                    queryset=UserChallengeCompletion.objects.filter(
                        completed_at__year=year, completed_at__month=month
                    ).order_by("completed_at"),
                    to_attr="_prefetched_completions",
                )
            )
        )

        context = {"request": request, "month": month, "year": year}
        serializer = AllChallengesCalendarSerializer(
            {"user_challenges": user_challenges}, context=context
        )
        return Response(serializer.data)


class ChallengeLeaderboardAPIView(ListAPIView):
    serializer_class = ChallengeLeaderboardSerializer
    permission_classes = [IsTelegramUser]

    def get_queryset(self):
        challenge_id = self.kwargs["id"]
        try:
            challenge = Challenge.objects.get(id=challenge_id)
        except Challenge.DoesNotExist:
            raise ValidationError("Challenge not found")

        # Query UserChallenge directly to get unique entries
        return (
            UserChallenge.objects.filter(
                challenge_id=challenge_id, highest_streak__gt=0
            )
            .select_related("user")
            .order_by("-highest_streak")
        )


class Challenge30DaysPlusStreakView(ListAPIView):
    serializer_class = Challenge30DaysPlusStreakSerializer
    permission_classes = [IsTelegramUser]

    def get_queryset(self):
        return (
            Challenge.objects.filter(user_challenges__highest_streak__gte=30)
            .distinct()
            .prefetch_related(
                Prefetch(
                    "user_challenges",
                    queryset=UserChallenge.objects.filter(highest_streak__gte=30)
                    .select_related("user")
                    .order_by("-highest_streak"),
                )
            )
        )


class Challenge30DaysPlusStreakDetailView(RetrieveAPIView):
    serializer_class = Challenge30DaysPlusStreakSerializer
    permission_classes = [IsTelegramUser]
    lookup_field = "id"

    def get_object(self):
        challenge_id = self.kwargs["id"]
        try:
            return (
                Challenge.objects.filter(
                    id=challenge_id, user_challenges__highest_streak__gte=30
                )
                .distinct()
                .prefetch_related(
                    Prefetch(
                        "user_challenges",
                        queryset=UserChallenge.objects.filter(highest_streak__gte=30)
                        .select_related("user")
                        .order_by("-highest_streak"),
                    )
                )
                .get()
            )
        except Challenge.DoesNotExist:
            raise ValidationError(
                "No users have achieved 30+ days streak in this challenge"
            )


class ChallengeAwardListView(ListAPIView):
    serializer_class = ChallengeAwardSerializer
    permission_classes = [IsTelegramUser]

    def get_queryset(self):
        return (
            ChallengeAward.objects.select_related("challenge")
            .prefetch_related(
                Prefetch(
                    "user_awards",
                    queryset=UserAward.objects.filter(user=self.request.user),
                    to_attr="_prefetched_user_awards",
                )
            )
            .all()
        )


class TournamentListAPIView(ListAPIView):
    serializer_class = TournamentListSerializer
    permission_classes = [IsTelegramUser]

    def get_queryset(self):
        now = timezone.now()
        return Tournament.objects.filter(is_active=True, finish_date__gte=now).order_by(
            "-created_at"
        )


class TournamentDetailAPIView(RetrieveAPIView):
    queryset = Tournament.objects.prefetch_related("challenges")
    serializer_class = TournamentDetailSerializer
    permission_classes = [IsTelegramUser]
    lookup_field = "id"


class UpdateUserChallengeStreaksAPIView(APIView):
    """
    API view to directly update all user challenge streaks.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        today = timezone.now().date()
        user_challenges = UserChallenge.objects.all()

        updated_count = 0
        for user_challenge in user_challenges:
            user_challenge.update_streak(today)
            updated_count += 1

        return Response(
            {
                "status": "success",
                "message": f"Updated {updated_count} user challenge streaks",
            },
            status=status.HTTP_200_OK,
        )
