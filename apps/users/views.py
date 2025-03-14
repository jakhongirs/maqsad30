import requests
from django.conf import settings
from django.db.models import Case, IntegerField, Value, When
from rest_framework import generics, permissions, status
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import Timezone, User
from apps.users.permissions import IsTelegramUser
from apps.users.tasks import update_channel_membership_status

from .serializers import (
    TelegramUserSerializer,
    TimezoneSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
)


class TelegramUserRegistrationView(generics.CreateAPIView):
    """
    API endpoint for registering new users via Telegram.
    This endpoint is public and does not require authentication.
    """

    serializer_class = TelegramUserSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def create(self, request, *args, **kwargs):
        # Check if user already exists
        telegram_id = request.data.get("telegram_id")
        existing_user = User.objects.filter(telegram_id=telegram_id).first()

        serializer = self.get_serializer(instance=existing_user, data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Set default timezone to Asia/Tashkent only for new users
        if not existing_user:
            timezone, created = Timezone.objects.get_or_create(
                name="Asia/Tashkent", defaults={"offset": "+05:00"}
            )
            user.timezone = timezone
            user.save(update_fields=["timezone"])

        status_code = status.HTTP_200_OK if existing_user else status.HTTP_201_CREATED
        return Response(
            {
                "status": "success",
                "message": "User updated successfully"
                if existing_user
                else "User registered successfully",
                "data": serializer.data,
            },
            status=status_code,
        )


class UserProfileRetrieveAPIView(RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsTelegramUser]

    def get_object(self):
        return self.request.user


class UserProfileUpdateAPIView(UpdateAPIView):
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [IsTelegramUser]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Return the full profile data after update
        return Response(
            UserProfileSerializer(instance, context={"request": request}).data
        )


class TimezoneListAPIView(ListAPIView):
    serializer_class = TimezoneSerializer
    permission_classes = [IsTelegramUser]
    filter_backends = [SearchFilter]
    search_fields = ["name", "name_en", "name_uz", "name_ru"]

    def get_queryset(self):
        queryset = Timezone.objects.all()
        user_timezone = self.request.user.timezone

        if user_timezone:
            # Use Case/When to prioritize user's timezone
            return queryset.annotate(
                is_user_timezone=Case(
                    When(id=user_timezone.id, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            ).order_by("is_user_timezone")

        return queryset


class LoadTimezoneDataAPIView(APIView):
    permission_classes = [IsTelegramUser]

    def post(self, request):
        try:
            import json

            # Read the JSON file
            with open("apps/users/fixtures/timezone.json", encoding="utf-8") as file:
                timezones = json.load(file)

            # Clear existing timezones
            Timezone.objects.all().delete()

            # Create new timezone objects
            for index, tz_data in enumerate(timezones, 1):
                timezone = Timezone.objects.create(offset=tz_data["offset"])

                # Set the same name for all languages including uz-cy
                languages = list(dict(settings.LANGUAGES).keys()) + ["uz-cy"]
                for lang_code in languages:
                    setattr(timezone, f"name_{lang_code}", tz_data["name"])
                timezone.save()

            return Response(
                {
                    "status": "success",
                    "message": f"{len(timezones)} timezones loaded successfully",
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CheckChannelMembershipAPIView(APIView):
    """
    API endpoint to check if a user is a member of a specified Telegram channel.
    This endpoint is public and accepts telegram_id in the request body.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        telegram_id = request.data.get("telegram_id") if request.data else None
        bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        channel_id = getattr(settings, "TELEGRAM_CHANNEL_ID", None)

        if not telegram_id:
            return Response(
                {"error": "telegram_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not bot_token:
            return Response(
                {"error": "TELEGRAM_BOT_TOKEN is not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not channel_id:
            return Response(
                {"error": "TELEGRAM_CHANNEL_ID is not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        url = f"https://api.telegram.org/bot{bot_token}/getChatMember"
        params = {"chat_id": channel_id, "user_id": telegram_id}

        try:
            response = requests.get(url, params=params)
            data = response.json()

            if "result" in data and "status" in data["result"]:
                member_status = data["result"]["status"]
                is_member = member_status in ["member", "administrator", "creator"]
            else:
                is_member = False

        except Exception as e:
            print(f"Error checking channel membership: {e}")
            is_member = False

        return Response({"is_member": is_member})


class UpdateChannelMembershipAPIView(APIView):
    """
    API endpoint to manually trigger the update of Telegram channel membership status for all users.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        task = update_channel_membership_status.delay()
        return Response(
            {
                "status": "success",
                "message": "Channel membership status update task has been queued",
                "task_id": task.id,
            }
        )
