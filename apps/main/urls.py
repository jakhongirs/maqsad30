from django.urls import path

from apps.main.views import ChallengeListAPIView

app_name = "main"

urlpatterns = [
    path("challenges/", ChallengeListAPIView.as_view(), name="challenge-list"),
]
