from rest_framework import generics, status
from rest_framework.response import Response

from .serializers import TelegramUserSerializer


class TelegramUserRegistrationView(generics.CreateAPIView):
    serializer_class = TelegramUserSerializer

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
