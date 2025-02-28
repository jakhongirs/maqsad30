from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.main.models import Challenge, UserChallenge, UserChallengeCompletion
from apps.main.serializers import (
    AllChallengesCalendarSerializer,
    ChallengeCalendarSerializer,
    ChallengeDetailSerializer,
    ChallengeListSerializer,
    UserChallengeCompletionSerializer,
)
from apps.users.permissions import IsTelegramUser


class ChallengeListAPIView(ListAPIView):
    queryset = Challenge.objects.all()
    serializer_class = ChallengeListSerializer
    permission_classes = [IsTelegramUser]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context


class ChallengeDetailAPIView(RetrieveAPIView):
    queryset = Challenge.objects.all()
    serializer_class = ChallengeDetailSerializer
    permission_classes = [IsTelegramUser]
    lookup_field = "id"

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

        # Get current time and date in user's timezone
        current_time = timezone.localtime().time()
        current_date = timezone.localdate()

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
    queryset = Challenge.objects.all()
    serializer_class = ChallengeCalendarSerializer
    permission_classes = [IsTelegramUser]
    lookup_field = "id"

    def get_serializer_context(self):
        context = super().get_serializer_context()
        try:
            month = int(self.request.query_params.get("month", timezone.now().month))
            year = int(self.request.query_params.get("year", timezone.now().year))
            # Validate month
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
        try:
            month = int(request.query_params.get("month", timezone.now().month))
            year = int(request.query_params.get("year", timezone.now().year))
            # Validate month
            if not 1 <= month <= 12:
                raise ValidationError("Month must be between 1 and 12")
        except ValueError:
            raise ValidationError("Invalid month or year format")

        context = {"request": request, "month": month, "year": year}
        serializer = AllChallengesCalendarSerializer(
            Challenge.objects.first(), context=context
        )
        return Response(serializer.data)
