from rest_framework.generics import ListAPIView

from apps.main.models import Challenge
from apps.main.serializers import ChallengeListSerializer
from apps.users.permissions import IsTelegramUser


class ChallengeListAPIView(ListAPIView):
    queryset = Challenge.objects.all()
    serializer_class = ChallengeListSerializer
    permission_classes = [IsTelegramUser]
