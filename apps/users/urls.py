from django.urls import path

from .views import TelegramUserRegistrationView, UserProfileAPIView

app_name = "users"

urlpatterns = [
    path(
        "telegram/register/",
        TelegramUserRegistrationView.as_view(),
        name="telegram-register",
    ),
    path("profile/", UserProfileAPIView.as_view(), name="user-profile"),
]
