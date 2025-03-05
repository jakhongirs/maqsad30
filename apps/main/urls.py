from django.urls import path

from apps.main.views import (
    AllChallengesCalendarAPIView,
    Challenge30DaysPlusStreakDetailView,
    Challenge30DaysPlusStreakView,
    ChallengeAwardListView,
    ChallengeCalendarAPIView,
    ChallengeLeaderboardAPIView,
    ChallengeListAPIView,
    TournamentDetailAPIView,
    TournamentListAPIView,
    UpdateUserChallengeStreaksAPIView,
    UserChallengeCompletionAPIView,
    UserChallengeCreateAPIView,
    UserChallengeDeleteAPIView,
    UserChallengeDetailAPIView,
    UserChallengeListAPIView,
)

app_name = "main"

urlpatterns = [
    # Tournament URLs
    path("tournaments/", TournamentListAPIView.as_view(), name="tournament-list"),
    path(
        "tournaments/<int:id>/",
        TournamentDetailAPIView.as_view(),
        name="tournament-detail",
    ),
    # Challenge URLs
    path("challenges/", ChallengeListAPIView.as_view(), name="challenge-list"),
    # User Challenge URLs
    path(
        "user-challenges/",
        UserChallengeListAPIView.as_view(),
        name="user-challenge-list",
    ),
    path(
        "user-challenges/create/",
        UserChallengeCreateAPIView.as_view(),
        name="user-challenge-create",
    ),
    path(
        "user-challenges/<int:id>/",
        UserChallengeDetailAPIView.as_view(),
        name="user-challenge-detail",
    ),
    path(
        "user-challenges/<int:id>/delete/",
        UserChallengeDeleteAPIView.as_view(),
        name="user-challenge-delete",
    ),
    path(
        "challenges/<int:id>/complete/",
        UserChallengeCompletionAPIView.as_view(),
        name="challenge-complete",
    ),
    path(
        "user-challenges/<int:id>/calendar/",
        ChallengeCalendarAPIView.as_view(),
        name="user-challenge-calendar",
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
    path(
        "challenges/awards/",
        ChallengeAwardListView.as_view(),
        name="challenge-awards",
    ),
    path(
        "admin/update-streaks/",
        UpdateUserChallengeStreaksAPIView.as_view(),
        name="update-user-challenge-streaks",
    ),
]
