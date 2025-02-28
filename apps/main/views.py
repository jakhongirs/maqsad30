from rest_framework.generics import ListAPIView, RetrieveAPIView

from apps.main.models import Challenge
from apps.main.serializers import ChallengeDetailSerializer, ChallengeListSerializer
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
