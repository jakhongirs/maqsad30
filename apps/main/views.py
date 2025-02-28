from rest_framework.generics import ListAPIView

from apps.main.models import Challenge
from apps.main.serializers import ChallengeListSerializer


class ChallengeListAPIView(ListAPIView):
    queryset = Challenge.objects.all()
    serializer_class = ChallengeListSerializer
