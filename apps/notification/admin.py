from django.contrib import admin

from apps.notification.models import Notification, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("type", "get_title", "get_related_object")
    list_filter = ("type",)
    search_fields = ("title", "message")

    def get_title(self, obj):
        return obj.title or "-"

    def get_related_object(self, obj):
        if obj.challenge:
            return obj.challenge.title
        elif obj.tournament:
            return obj.tournament.title
        return "-"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("template", "user", "sent_at")
    list_filter = ("sent_at", "template__type")
    search_fields = ("user__first_name", "user__last_name", "template__title")
    raw_id_fields = ("user", "template")
