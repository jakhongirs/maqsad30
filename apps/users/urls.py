from django.urls import path

from .views import TelegramUserRegistrationView

app_name = "users"

urlpatterns = [
    path(
        "telegram/register/",
        TelegramUserRegistrationView.as_view(),
        name="telegram-register",
    ),
]
