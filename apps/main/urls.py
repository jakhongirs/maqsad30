from django.urls import path

from apps.main.views import ChallengeDetailAPIView, ChallengeListAPIView

app_name = "main"

urlpatterns = [
    path("challenges/", ChallengeListAPIView.as_view(), name="challenge-list"),
    path(
        "challenges/<int:id>/",
        ChallengeDetailAPIView.as_view(),
        name="challenge-detail",
    ),
]
