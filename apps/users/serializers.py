from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.users.models import Timezone, User

User = get_user_model()


class TelegramUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "telegram_id",
            "telegram_username",
            "first_name",
            "last_name",
            "telegram_photo_url",
            "telegram_photo",
        ]
        read_only_fields = ["telegram_photo"]

    def create(self, validated_data):
        telegram_username = validated_data.get("telegram_username")
        if telegram_username and telegram_username.startswith("@"):
            validated_data["telegram_username"] = telegram_username[1:]

        user, created = User.objects.update_or_create(
            telegram_id=validated_data["telegram_id"],
            defaults={
                "first_name": validated_data.get("first_name", ""),
                "last_name": validated_data.get("last_name", ""),
                "telegram_username": validated_data.get("telegram_username"),
                "telegram_photo_url": validated_data.get("telegram_photo_url"),
                "username": validated_data.get("telegram_username"),
            },
        )
        return user


class TimezoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timezone
        fields = ("id", "name", "offset")


class UserProfileSerializer(serializers.ModelSerializer):
    timezone = TimezoneSerializer(read_only=True)
    telegram_photo = serializers.SerializerMethodField()

    def get_telegram_photo(self, obj):
        request = self.context.get("request")
        if obj.telegram_photo:
            return request.build_absolute_uri(obj.telegram_photo.url)
        return obj.telegram_photo_url

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "telegram_username",
            "telegram_photo",
            "language",
            "timezone",
            "is_onboarding_finished",
        )
        read_only_fields = fields


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    timezone_id = serializers.PrimaryKeyRelatedField(
        queryset=Timezone.objects.all(),
        source="timezone",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "language",
            "timezone_id",
        )
