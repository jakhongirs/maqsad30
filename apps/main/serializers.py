from rest_framework import serializers

from apps.main.models import Challenge, UserChallenge


class ChallengeListSerializer(serializers.ModelSerializer):
    current_streak = serializers.SerializerMethodField()

    def get_current_streak(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0

        user_challenge = UserChallenge.objects.filter(
            user=request.user, challenge=obj
        ).first()

        return user_challenge.current_streak if user_challenge else 0

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
            "current_streak",
        )
