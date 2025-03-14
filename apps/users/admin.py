from django.contrib import admin

from .models import Timezone, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "created_at")
    list_filter = ("is_active", "is_staff", "is_telegram_channel_member")
    search_fields = ("username", "email", "first_name", "last_name")


@admin.register(Timezone)
class TimezoneAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "offset")
    search_fields = ("name", "offset")
