from django.contrib.auth import get_user_model
from rest_framework import serializers

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
