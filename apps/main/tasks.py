import logging

from celery import shared_task
from django.utils import timezone

from apps.main.models import UserChallenge

logger = logging.getLogger(__name__)


@shared_task
def update_all_user_challenge_streaks():
    """
    Update streaks for all user challenges.
    This task is meant to be run daily to ensure streaks are properly updated
    even if users don't actively complete challenges.
    """
    today = timezone.now().date()

    # Get all user challenges
    user_challenges = UserChallenge.objects.all()

    updated_count = 0
    for user_challenge in user_challenges:
        # Call the update_streak method with today's date
        # This will recalculate streaks based on completion history
        user_challenge.update_streak(today)
        updated_count += 1

    return f"Updated {updated_count} user challenge streaks"
