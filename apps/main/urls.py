from django.urls import path

from apps.main.views import (
    AllChallengesCalendarAPIView,
    Challenge30DaysPlusStreakDetailView,
    Challenge30DaysPlusStreakView,
    ChallengeCalendarAPIView,
    ChallengeDetailAPIView,
    ChallengeLeaderboardAPIView,
    ChallengeListAPIView,
    UserChallengeCompletionAPIView,
)

app_name = "main"

urlpatterns = [
    path("challenges/", ChallengeListAPIView.as_view(), name="challenge-list"),
    path(
        "challenges/<int:id>/",
        ChallengeDetailAPIView.as_view(),
        name="challenge-detail",
    ),
    path(
        "challenges/<int:id>/complete/",
        UserChallengeCompletionAPIView.as_view(),
        name="challenge-complete",
    ),
    path(
        "challenges/<int:id>/calendar/",
        ChallengeCalendarAPIView.as_view(),
        name="challenge-calendar",
    ),
    path(
        "challenges/calendar/",
        AllChallengesCalendarAPIView.as_view(),
        name="all-challenges-calendar",
    ),
    path(
        "challenges/<int:id>/leaderboard/",
        ChallengeLeaderboardAPIView.as_view(),
        name="challenge-leaderboard",
    ),
    path(
        "challenges/30-days-plus-streaks/",
        Challenge30DaysPlusStreakView.as_view(),
        name="challenge-30-days-plus-streaks",
    ),
    path(
        "challenges/<int:id>/30-days-plus-streaks/",
        Challenge30DaysPlusStreakDetailView.as_view(),
        name="challenge-30-days-plus-streaks-detail",
    ),
]
