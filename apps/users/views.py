from rest_framework import generics, permissions, status
from rest_framework.generics import RetrieveAPIView, UpdateAPIView
from rest_framework.response import Response

from apps.users.permissions import IsTelegramUser

from .serializers import (
    TelegramUserSerializer,
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
