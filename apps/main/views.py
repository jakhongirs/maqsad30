from django.db.models import Prefetch
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
    SuperChallenge,
    SuperChallengeAward,
    UserAward,
    UserChallenge,
    UserChallengeCompletion,
    UserSuperAward,
    UserSuperChallenge,
    UserSuperChallengeCompletion,
)
from apps.main.serializers import (
    AllChallengesCalendarSerializer,
    AllSuperChallengesCalendarSerializer,
    Challenge30DaysPlusStreakSerializer,
    ChallengeAwardSerializer,
    ChallengeCalendarSerializer,
    ChallengeDetailSerializer,
    ChallengeLeaderboardSerializer,
    ChallengeListSerializer,
    SuperChallengeAwardSerializer,
    SuperChallengeCalendarSerializer,
    SuperChallengeDetailSerializer,
    SuperChallengeLeaderboardSerializer,
    SuperChallengeListSerializer,
    UserChallengeCompletionSerializer,
    UserChallengeCreateSerializer,
    UserChallengeDetailSerializer,
    UserChallengeListSerializer,
    UserSuperChallengeDetailSerializer,
    UserSuperChallengeListSerializer,
)
from apps.main.tasks import update_all_user_challenge_streaks
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


class ChallengeDetailAPIView(RetrieveAPIView):
    serializer_class = ChallengeDetailSerializer
    permission_classes = [IsTelegramUser]
    lookup_field = "id"

    def get_queryset(self):
        return Challenge.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
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
        elif not user_challenge.is_active:
            # If challenge exists but is inactive, reactivate it
            user_challenge.reactivate()

        # Check if user has already completed the challenge today
        already_completed = UserChallengeCompletion.objects.filter(
            user_challenge=user_challenge,
            completed_at__date=current_date,
            is_active=True,
        ).exists()

        if already_completed:
            raise ValidationError("You have already completed this challenge today")

        # Create completion
        completion = serializer.save(user_challenge=user_challenge)

        # Update streak
        user_challenge.update_streak(current_date)

        # Check if this challenge is part of any active super challenges
        # and update them if all challenges in the super challenge are completed
        self.check_and_update_super_challenges(challenge)

        return completion

    def check_and_update_super_challenges(self, challenge):
        """
        Check if the completed challenge is part of any super challenges,
        and if so, check if all challenges in those super challenges are completed.
        If all are completed, create a completion record for the super challenge.
        """
        today = timezone.now().date()

        # Get all active super challenges that include this challenge
        super_challenges = SuperChallenge.objects.filter(
            challenges=challenge, start_date__lte=today, end_date__gte=today
        )

        for super_challenge in super_challenges:
            # Get or create the user super challenge
            user_super_challenge, created = UserSuperChallenge.objects.get_or_create(
                user=self.request.user,
                super_challenge=super_challenge,
                defaults={"is_active": True, "is_failed": False},
            )

            # If the user super challenge is failed, skip it
            if user_super_challenge.is_failed:
                continue

            # Check if all challenges in this super challenge are completed today
            # and create a completion if they are
            user_super_challenge.check_and_create_completion()


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

        # Let the serializer handle the creation or reactivation
        user_challenge = serializer.save()

        # Return appropriate response
        response_serializer = UserChallengeListSerializer(user_challenge)

        # If it's a new challenge, return 201, otherwise 200
        status_code = status.HTTP_201_CREATED
        if hasattr(user_challenge, "_reactivated") and user_challenge._reactivated:
            status_code = status.HTTP_200_OK

        return Response(response_serializer.data, status=status_code)


class UserChallengeListAPIView(ListAPIView):
    serializer_class = UserChallengeListSerializer
    permission_classes = [IsTelegramUser]

    def get_queryset(self):
        return (
            UserChallenge.objects.filter(user=self.request.user, is_active=True)
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
        instance.delete()  # This will use our custom delete() method that deactivates instead of deleting
        return Response(
            {"status": "success", "message": "Challenge deactivated successfully"},
            status=status.HTTP_200_OK,
        )


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


# Super Challenge views
class SuperChallengeListAPIView(ListAPIView):
    serializer_class = SuperChallengeListSerializer
    permission_classes = [IsTelegramUser]

    def get_queryset(self):
        today = timezone.now().date()
        return SuperChallenge.objects.filter(
            start_date__lte=today, end_date__gte=today
        ).order_by("start_date")


class SuperChallengeDetailAPIView(RetrieveAPIView):
    serializer_class = SuperChallengeDetailSerializer
    permission_classes = [IsTelegramUser]
    lookup_field = "id"

    def get_queryset(self):
        return SuperChallenge.objects.all().prefetch_related("challenges")


class UserSuperChallengeListAPIView(ListAPIView):
    serializer_class = UserSuperChallengeListSerializer
    permission_classes = [IsTelegramUser]

    def get_queryset(self):
        today = timezone.now().date()
        return (
            UserSuperChallenge.objects.filter(
                user=self.request.user,
                is_failed=False,
                super_challenge__start_date__lte=today,
                super_challenge__end_date__gte=today,
            )
            .select_related("super_challenge")
            .order_by("-current_streak", "-created_at")
        )


class UserSuperChallengeDetailAPIView(RetrieveAPIView):
    serializer_class = UserSuperChallengeDetailSerializer
    permission_classes = [IsTelegramUser]
    lookup_field = "id"

    def get_queryset(self):
        return (
            UserSuperChallenge.objects.filter(user=self.request.user)
            .select_related("super_challenge")
            .prefetch_related("super_challenge__challenges")
        )


class SuperChallengeCalendarAPIView(RetrieveAPIView):
    serializer_class = SuperChallengeCalendarSerializer
    permission_classes = [IsTelegramUser]
    lookup_field = "id"

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return UserSuperChallenge.objects.none()

        try:
            month = int(self.request.query_params.get("month", timezone.now().month))
            year = int(self.request.query_params.get("year", timezone.now().year))
            if not 1 <= month <= 12:
                raise ValidationError("Month must be between 1 and 12")
        except ValueError:
            raise ValidationError("Invalid month or year format")

        return (
            UserSuperChallenge.objects.filter(user=self.request.user)
            .select_related("super_challenge")
            .prefetch_related(
                Prefetch(
                    "completions",
                    queryset=UserSuperChallengeCompletion.objects.filter(
                        completed_at__year=year, completed_at__month=month
                    ),
                    to_attr="_prefetched_completions",
                )
            )
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            context["month"] = int(
                self.request.query_params.get("month", timezone.now().month)
            )
            context["year"] = int(
                self.request.query_params.get("year", timezone.now().year)
            )
        except ValueError:
            context["month"] = timezone.now().month
            context["year"] = timezone.now().year

        return context


class AllSuperChallengesCalendarAPIView(APIView):
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
        user_super_challenges = (
            UserSuperChallenge.objects.filter(user=request.user)
            .select_related("super_challenge")
            .prefetch_related(
                Prefetch(
                    "completions",
                    queryset=UserSuperChallengeCompletion.objects.filter(
                        completed_at__year=year, completed_at__month=month
                    ).order_by("completed_at"),
                    to_attr="_prefetched_completions",
                )
            )
        )

        context = {"request": request, "month": month, "year": year}
        serializer = AllSuperChallengesCalendarSerializer(
            {"user_super_challenges": user_super_challenges}, context=context
        )
        return Response(serializer.data)


class SuperChallengeAwardListView(ListAPIView):
    serializer_class = SuperChallengeAwardSerializer
    permission_classes = [IsTelegramUser]

    def get_queryset(self):
        return (
            SuperChallengeAward.objects.all()
            .select_related("super_challenge")
            .prefetch_related(
                Prefetch(
                    "user_super_awards",
                    queryset=UserSuperAward.objects.filter(user=self.request.user),
                    to_attr="_prefetched_user_awards",
                )
            )
        )


class SuperChallengeLeaderboardAPIView(ListAPIView):
    serializer_class = SuperChallengeLeaderboardSerializer
    permission_classes = [IsTelegramUser]

    def get_queryset(self):
        super_challenge_id = self.kwargs["id"]
        try:
            super_challenge = SuperChallenge.objects.get(id=super_challenge_id)
        except SuperChallenge.DoesNotExist:
            raise ValidationError("Super Challenge not found")

        # Query UserSuperChallenge directly to get unique entries
        return (
            UserSuperChallenge.objects.filter(
                super_challenge_id=super_challenge_id, highest_streak__gt=0
            )
            .select_related("user")
            .order_by("-highest_streak")
        )
