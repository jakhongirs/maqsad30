from rest_framework import generics, permissions, status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response

from apps.users.permissions import IsTelegramUser

from .serializers import TelegramUserSerializer, UserProfileSerializer


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


class UserProfileAPIView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsTelegramUser]

    def get_object(self):
        return self.request.user
