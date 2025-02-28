from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class IsTelegramUser(permissions.BasePermission):
    message = "User must be authenticated with a Telegram account"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise PermissionDenied("Authentication required")
        if not request.user.telegram_id:
            raise PermissionDenied("Only Telegram users are allowed")
        return True
