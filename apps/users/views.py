from rest_framework import generics, permissions, status
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import Timezone
from apps.users.permissions import IsTelegramUser

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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "status": "success",
                "message": "User registered successfully",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
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
    queryset = Timezone.objects.all()
    serializer_class = TimezoneSerializer
    permission_classes = [IsTelegramUser]
    filter_backends = [SearchFilter]
    search_fields = ["name", "name_en", "name_uz", "name_ru"]


class LoadTimezoneDataAPIView(APIView):
    permission_classes = [IsTelegramUser]

    def post(self, request):
        try:
            import json

            from django.conf import settings

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
