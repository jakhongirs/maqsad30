from django.urls import path

from .views import (
    TelegramUserRegistrationView,
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
]
