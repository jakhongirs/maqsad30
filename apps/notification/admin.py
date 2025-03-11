from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.notification.models import (
    ChallengeNotificationTemplate,
    NotificationLog,
    SuperChallengeNotificationTemplate,
)


@admin.register(ChallengeNotificationTemplate)
class ChallengeNotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("challenge", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("challenge__title",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("challenge", "message", "is_active")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )


@admin.register(SuperChallengeNotificationTemplate)
class SuperChallengeNotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("super_challenge", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("super_challenge__title",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("super_challenge", "is_active")}),
        (
            _("Messages"),
            {
                "fields": (
                    "general_message",
                    "progress_warning_message",
                    "failure_message",
                ),
                "classes": ("collapse",),
            },
        ),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "is_sent", "sent_at")
    list_filter = ("notification_type", "is_sent", "sent_at")
    search_fields = ("user__username", "user__first_name", "user__last_name", "message")
    readonly_fields = (
        "user",
        "challenge",
        "super_challenge",
        "message",
        "notification_type",
        "sent_at",
        "is_sent",
        "error_message",
    )
    fieldsets = (
        (None, {"fields": ("user", "notification_type", "is_sent", "sent_at")}),
        (_("Related Objects"), {"fields": ("challenge", "super_challenge")}),
        (_("Message"), {"fields": ("message",)}),
        (_("Error"), {"fields": ("error_message",), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
