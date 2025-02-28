from django.contrib import admin

from apps.main.models import Challenge


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "start_time", "end_time")
    list_filter = ("start_time", "end_time")
    search_fields = ("title",)
