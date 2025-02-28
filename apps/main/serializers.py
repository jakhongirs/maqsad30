from rest_framework import serializers

from apps.main.models import Challenge


class ChallengeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = (
            "id",
            "title",
            "icon",
            "video_instruction_url",
            "start_time",
            "end_time",
            "created_at",
            "updated_at",
        )
