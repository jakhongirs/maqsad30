from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()


class TelegramAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        if request.path.startswith("/swagger/") or request.path.startswith("/redoc/"):
            return None

        telegram_id = request.headers.get("X-Telegram-ID")

        if not telegram_id:
            raise AuthenticationFailed("X-Telegram-ID header is required")

        try:
            user = User.objects.get(telegram_id=telegram_id)
            return (user, None)
        except User.DoesNotExist:
            raise AuthenticationFailed("No user found with this Telegram ID")
