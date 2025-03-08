from datetime import datetime, timedelta

from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
)
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
    UserTournament,
    UserTournamentDay,
)
from apps.main.serializers import (
    AllChallengesCalendarSerializer,
    Challenge30DaysPlusStreakSerializer,
    ChallengeAwardSerializer,
    ChallengeCalendarSerializer,
    ChallengeLeaderboardSerializer,
    ChallengeListSerializer,
    TournamentCalendarSerializer,
    TournamentChallengeCalendarSerializer,
    TournamentChallengeListSerializer,
    TournamentDetailSerializer,
    TournamentLeaderboardSerializer,
    TournamentListSerializer,
    UserChallengeCompletionSerializer,
    UserChallengeCreateSerializer,
    UserChallengeDetailSerializer,
    UserChallengeListSerializer,
)
from apps.main.tasks import update_all_user_challenge_streaks
from apps.users.models import User
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


class UserChallengeCompletionAPIView(CreateAPIView):
    serializer_class = UserChallengeCompletionSerializer
    permission_classes = [IsTelegramUser]

    def perform_create(self, serializer):
        challenge_id = self.kwargs["id"]
        try:
            challenge = Challenge.objects.get(id=challenge_id)
        except Challenge.DoesNotExist:
            raise ValidationError("Challenge not found")

        # Get current date in UTC
        now = timezone.now()
        current_date = now.date()

        # Get existing UserChallenge or create new one
        user_challenge = UserChallenge.objects.filter(
            user=self.request.user, challenge=challenge
        ).first()

        if not user_challenge:
            # Create new UserChallenge if none exists
            user_challenge = UserChallenge.objects.create(
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

        # Handle tournament progress if challenge is part of active tournaments
        active_tournaments = Tournament.objects.filter(
            challenges=challenge, is_active=True, finish_date__gte=now
        )

        for tournament in active_tournaments:
            user_tournament, _ = UserTournament.objects.get_or_create(
                user=self.request.user, tournament=tournament
            )

            if not user_tournament.is_failed:
                # Get or create today's tournament day record
                day_record, _ = UserTournamentDay.objects.get_or_create(
                    user_tournament=user_tournament, date=current_date
                )

                # Add the completed challenge to the day's record
                day_record.completed_challenges.add(challenge)

                # Just update completion status without checking failures
                # Failures will be checked by the end-of-day Celery task
                day_record.update_completion_status()

        return completion


class ChallengeCalendarAPIView(RetrieveAPIView):
    serializer_class = ChallengeCalendarSerializer
    permission_classes = [IsTelegramUser]
    lookup_field = "id"

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return UserChallenge.objects.none()

        try:
            month = int(self.request.query_params.get("month", timezone.now().month))
            year = int(self.request.query_params.get("year", timezone.now().year))
            if not 1 <= month <= 12:
                raise ValidationError("Month must be between 1 and 12")
        except ValueError:
            raise ValidationError("Invalid month or year format")

        return (
            UserChallenge.objects.filter(user=self.request.user)
            .select_related("challenge")
            .prefetch_related(
                Prefetch(
                    "completions",
                    queryset=UserChallengeCompletion.objects.filter(
                        completed_at__year=year, completed_at__month=month
                    ),
                    to_attr="_prefetched_completions",
                )
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
        today = now.date()
        if not self.request.user.is_authenticated:
            return Tournament.objects.filter(
                is_active=True, finish_date__gte=now
            ).prefetch_related("challenges")

        return (
            Tournament.objects.filter(is_active=True, finish_date__gte=now)
            .prefetch_related(
                Prefetch(
                    "challenges",
                    queryset=Challenge.objects.prefetch_related(
                        Prefetch(
                            "user_challenges",
                            queryset=UserChallenge.objects.filter(
                                user=self.request.user
                            ).prefetch_related(
                                Prefetch(
                                    "completions",
                                    queryset=UserChallengeCompletion.objects.filter(
                                        completed_at__date=today
                                    ),
                                    to_attr="_prefetched_completions_today",
                                )
                            ),
                            to_attr="_prefetched_user_challenges",
                        )
                    ),
                )
            )
            .order_by("-created_at")
        )


class UpdateUserChallengeStreaksAPIView(APIView):
    """
    API view to trigger the Celery task that updates all user challenge streaks.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        # Trigger the Celery task
        task = update_all_user_challenge_streaks.delay()

        return Response(
            {
                "status": "success",
                "message": "Started updating user challenge streaks",
                "task_id": str(task.id),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class UserChallengeCreateAPIView(CreateAPIView):
    serializer_class = UserChallengeCreateSerializer
    permission_classes = [IsTelegramUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Check if challenge exists
        challenge_id = serializer.validated_data["challenge"].id
        existing_challenge = UserChallenge.objects.filter(
            user=request.user, challenge_id=challenge_id
        ).first()

        if existing_challenge:
            # Return existing challenge
            response_serializer = UserChallengeListSerializer(existing_challenge)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        # Create new challenge
        user_challenge = serializer.save()

        # Handle tournament creation if challenge is part of active tournaments
        now = timezone.now()
        active_tournaments = Tournament.objects.filter(
            challenges=user_challenge.challenge, is_active=True, finish_date__gte=now
        )

        for tournament in active_tournaments:
            UserTournament.objects.get_or_create(
                user=request.user, tournament=tournament
            )

        response_serializer = UserChallengeListSerializer(user_challenge)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class UserChallengeListAPIView(ListAPIView):
    serializer_class = UserChallengeListSerializer
    permission_classes = [IsTelegramUser]

    def get_queryset(self):
        return (
            UserChallenge.objects.filter(user=self.request.user)
            .select_related("challenge")
            .order_by("-current_streak", "-created_at")
        )


class UserChallengeDeleteAPIView(DestroyAPIView):
    permission_classes = [IsTelegramUser]
    lookup_field = "id"

    def get_queryset(self):
        return UserChallenge.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()  # This will use our custom delete() method that handles the 30-day streak logic
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserChallengeDetailAPIView(RetrieveAPIView):
    serializer_class = UserChallengeDetailSerializer
    permission_classes = [IsTelegramUser]
    lookup_field = "id"

    def get_queryset(self):
        today = timezone.now().date()
        return (
            UserChallenge.objects.filter(user=self.request.user)
            .select_related("challenge")
            .prefetch_related(
                Prefetch(
                    "completions",
                    queryset=UserChallengeCompletion.objects.filter(
                        completed_at__date=today
                    ),
                    to_attr="_prefetched_completions_today",
                )
            )
        )


class UserTournamentAPIView(RetrieveAPIView):
    """
    API view to get tournament details with current user's participation data
    """

    serializer_class = TournamentDetailSerializer
    permission_classes = [IsTelegramUser]
    lookup_url_kwarg = "tournament_id"

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Tournament.objects.prefetch_related("challenges")

        return Tournament.objects.prefetch_related(
            Prefetch(
                "challenges",
                queryset=Challenge.objects.prefetch_related(
                    Prefetch(
                        "user_challenges",
                        queryset=UserChallenge.objects.filter(user=self.request.user),
                        to_attr="_prefetched_user_challenges",
                    )
                ),
            )
        )


class ChallengeDetailAPIView(RetrieveAPIView):
    """
    API view to get challenge details with user's participation data
    """

    serializer_class = TournamentChallengeListSerializer
    permission_classes = [IsTelegramUser]
    lookup_field = "id"

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Challenge.objects.all()

        today = timezone.now().date()
        return Challenge.objects.prefetch_related(
            Prefetch(
                "user_challenges",
                queryset=UserChallenge.objects.filter(
                    user=self.request.user
                ).prefetch_related(
                    Prefetch(
                        "completions",
                        queryset=UserChallengeCompletion.objects.filter(
                            completed_at__date=today
                        ),
                        to_attr="_prefetched_completions_today",
                    )
                ),
                to_attr="_prefetched_user_challenges",
            )
        )


class TournamentCalendarAPIView(RetrieveAPIView):
    """
    API view to get tournament calendar data showing completed days and challenges
    """

    serializer_class = TournamentCalendarSerializer
    permission_classes = [IsTelegramUser]
    lookup_url_kwarg = "tournament_id"

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Tournament.objects.none()

        return Tournament.objects.prefetch_related(
            "challenges",
            Prefetch(
                "user_tournaments",
                queryset=UserTournament.objects.filter(user=self.request.user),
                to_attr="_prefetched_user_tournaments",
            ),
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


class TournamentChallengeCalendarAPIView(RetrieveAPIView):
    """
    API view to get tournament calendar data for a specific challenge
    """

    serializer_class = TournamentChallengeCalendarSerializer
    permission_classes = [IsTelegramUser]
    lookup_url_kwarg = "tournament_id"

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Tournament.objects.none()

        return Tournament.objects.prefetch_related(
            "challenges",
            Prefetch(
                "user_tournaments",
                queryset=UserTournament.objects.filter(user=self.request.user),
                to_attr="_prefetched_user_tournaments",
            ),
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

        # Get the challenge
        challenge_id = self.kwargs.get("challenge_id")
        try:
            challenge = Challenge.objects.get(id=challenge_id)
        except Challenge.DoesNotExist:
            raise ValidationError("Challenge not found")

        context["month"] = month
        context["year"] = year
        context["challenge"] = challenge
        return context


class TournamentLeaderboardAPIView(ListAPIView):
    """
    API view to get tournament leaderboard data showing user, completed days, and failure status
    """

    serializer_class = TournamentLeaderboardSerializer
    permission_classes = [IsTelegramUser]

    def get_queryset(self):
        tournament_id = self.kwargs.get("tournament_id")
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError("Tournament not found")

        # Get all user tournaments for this tournament
        return (
            UserTournament.objects.filter(tournament=tournament)
            .select_related("user", "tournament")
            .prefetch_related("daily_records")
            .annotate(
                completed_days=Count(
                    "daily_records", filter=Q(daily_records__is_completed=True)
                )
            )
            .order_by("-completed_days", "is_failed")
            .distinct()
        )


class BackfillUserChallengeCompletionAPIView(APIView):
    """
    API view to backfill UserChallengeCompletion data from March 1st to March 6th
    for all challenges and users.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        # Set the date range
        start_date = datetime(2025, 3, 1, tzinfo=timezone.get_current_timezone())
        end_date = datetime(2025, 3, 6, tzinfo=timezone.get_current_timezone())
        current_date = start_date

        # Get all challenges and non-staff users
        challenges = Challenge.objects.all()
        users = User.objects.filter(is_staff=False)

        created_completions = 0
        created_user_challenges = 0

        while current_date <= end_date:
            # For each challenge and user
            for challenge in challenges:
                for user in users:
                    # Get or create UserChallenge
                    user_challenge, uc_created = UserChallenge.objects.get_or_create(
                        user=user,
                        challenge=challenge,
                        defaults={"started_at": start_date},
                    )

                    if uc_created:
                        created_user_challenges += 1

                    # Check if completion exists for this date
                    completion_exists = UserChallengeCompletion.objects.filter(
                        user_challenge=user_challenge,
                        completed_at__date=current_date.date(),
                    ).exists()

                    if not completion_exists:
                        # Create completion at challenge's start_time for the current date
                        completion_time = timezone.datetime.combine(
                            current_date.date(),
                            challenge.start_time,
                            tzinfo=timezone.get_current_timezone(),
                        )

                        UserChallengeCompletion.objects.create(
                            user_challenge=user_challenge, completed_at=completion_time
                        )
                        created_completions += 1

            current_date += timedelta(days=1)

        # Update streaks for all user challenges
        for user_challenge in UserChallenge.objects.filter(user__is_staff=False):
            user_challenge.update_streak(end_date.date())

        return Response(
            {
                "status": "success",
                "message": f"Successfully backfilled data from {start_date.date()} to {end_date.date()}",
                "created_user_challenges": created_user_challenges,
                "created_completions": created_completions,
            },
            status=status.HTTP_200_OK,
        )


class DeleteIncorrectCompletionsAPIView(APIView):
    """
    API view to delete UserChallengeCompletion data from March 1st to March 6th 2024
    that were incorrectly created with wrong year.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        # Set the date range for incorrect data
        start_date = datetime(2024, 3, 1, tzinfo=timezone.get_current_timezone())
        end_date = datetime(2024, 3, 6, tzinfo=timezone.get_current_timezone())

        # Get completions in the incorrect date range
        incorrect_completions = UserChallengeCompletion.objects.filter(
            completed_at__date__gte=start_date.date(),
            completed_at__date__lte=end_date.date(),
            user_challenge__user__is_staff=False,  # Only for non-staff users
        )

        # Count completions before deletion
        completions_count = incorrect_completions.count()

        # Get affected user challenges
        affected_user_challenges = UserChallenge.objects.filter(
            completions__in=incorrect_completions
        ).distinct()
        user_challenges_count = affected_user_challenges.count()

        # Delete the completions
        incorrect_completions.delete()

        # Update streaks for affected user challenges
        for user_challenge in affected_user_challenges:
            user_challenge.update_streak(timezone.now().date())

        return Response(
            {
                "status": "success",
                "message": f"Successfully deleted incorrect completions from {start_date.date()} to {end_date.date()}",
                "deleted_completions": completions_count,
                "affected_user_challenges": user_challenges_count,
            },
            status=status.HTTP_200_OK,
        )


class BackfillTournamentDataAPIView(APIView):
    """
    API view to create UserTournament and UserTournamentDay records based on existing
    UserChallengeCompletion data from March 1st to March 6th 2025.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        # Set the date range
        start_date = datetime(2025, 3, 1, tzinfo=timezone.get_current_timezone())
        end_date = datetime(2025, 3, 7, tzinfo=timezone.get_current_timezone())
        current_date = start_date

        # Get all active tournaments for that period
        tournaments = Tournament.objects.filter(is_active=True)

        created_user_tournaments = 0
        created_tournament_days = 0
        updated_tournament_days = 0

        # Process each tournament
        for tournament in tournaments:
            # Get all challenge completions for tournament challenges in the date range
            challenge_completions = UserChallengeCompletion.objects.filter(
                user_challenge__challenge__in=tournament.challenges.all(),
                completed_at__date__gte=start_date.date(),
                completed_at__date__lte=end_date.date(),
                user_challenge__user__is_staff=False,  # Only for non-staff users
            ).select_related("user_challenge__user", "user_challenge__challenge")

            # Group completions by user and date
            user_date_completions = {}
            for completion in challenge_completions:
                user = completion.user_challenge.user
                date = completion.completed_at.date()
                challenge = completion.user_challenge.challenge

                if user not in user_date_completions:
                    user_date_completions[user] = {}
                if date not in user_date_completions[user]:
                    user_date_completions[user][date] = set()
                user_date_completions[user][date].add(challenge)

            # Create UserTournament and UserTournamentDay records
            for user, date_completions in user_date_completions.items():
                # Create or get UserTournament
                user_tournament, ut_created = UserTournament.objects.get_or_create(
                    user=user,
                    tournament=tournament,
                    defaults={"started_at": start_date, "is_failed": False},
                )
                if ut_created:
                    created_user_tournaments += 1

                # Create UserTournamentDay records for each date
                for date, completed_challenges in date_completions.items():
                    (
                        tournament_day,
                        td_created,
                    ) = UserTournamentDay.objects.get_or_create(
                        user_tournament=user_tournament,
                        date=date,
                    )
                    if td_created:
                        created_tournament_days += 1

                    # Add completed challenges
                    tournament_day.completed_challenges.add(*completed_challenges)

                    # Update completion status
                    tournament_day.update_completion_status()
                    updated_tournament_days += 1

                # Update tournament failure status
                user_tournament.update_failures(end_date.date())

        return Response(
            {
                "status": "success",
                "message": f"Successfully created tournament data from {start_date.date()} to {end_date.date()}",
                "created_user_tournaments": created_user_tournaments,
                "created_tournament_days": created_tournament_days,
                "updated_tournament_days": updated_tournament_days,
            },
            status=status.HTTP_200_OK,
        )
