from django.urls import path

from .views import (
    LoadTimezoneDataAPIView,
    TelegramUserRegistrationView,
    TimezoneListAPIView,
    UserProfileRetrieveAPIView,
    UserProfileUpdateAPIView,
)

app_name = "users"

urlpatterns = [
    path(
        "telegram/register/",
        TelegramUserRegistrationView.as_view(),
        name="telegram-register",
    ),
    path("profile/", UserProfileRetrieveAPIView.as_view(), name="user-profile"),
    path(
        "profile/update/",
        UserProfileUpdateAPIView.as_view(),
        name="user-profile-update",
    ),
    path("timezones/", TimezoneListAPIView.as_view(), name="timezone-list"),
    path("timezones/load/", LoadTimezoneDataAPIView.as_view(), name="timezone-load"),
]
