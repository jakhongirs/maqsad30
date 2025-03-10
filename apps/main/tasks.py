import logging

from celery import shared_task
from django.utils import timezone

from apps.main.models import UserChallenge, UserSuperChallenge

logger = logging.getLogger(__name__)


@shared_task
def update_all_user_challenge_streaks():
    """
    Update streaks for all active user challenges and super challenges.
    This task is meant to be run daily to ensure streaks are properly updated
    even if users don't actively complete challenges.
    """
    today = timezone.now().date()

    # Get all active user challenges
    user_challenges = UserChallenge.objects.filter(is_active=True)

    updated_count = 0
    for user_challenge in user_challenges:
        # Call the update_streak method with today's date
        # This will recalculate streaks based on completion history
        user_challenge.update_streak(today)
        updated_count += 1

    # Get all active user super challenges that haven't failed yet
    user_super_challenges = UserSuperChallenge.objects.filter(
        is_active=True,
        is_failed=False,
        super_challenge__start_date__lte=today,
        super_challenge__end_date__gte=today,
    )

    super_updated_count = 0
    super_failed_count = 0

    for user_super_challenge in user_super_challenges:
        # Check if the super challenge has failed based on previous days
        # has_failed() will update streak information if the challenge has failed
        if user_super_challenge.has_failed():
            super_failed_count += 1
            continue

        # If not failed, update the streak
        user_super_challenge.update_streak(today)
        super_updated_count += 1

    # Also check for any challenges that were previously marked as failed
    # but need their streak information updated
    failed_challenges = UserSuperChallenge.objects.filter(
        is_active=True, is_failed=True, super_challenge__end_date__gte=today
    )

    failed_updated_count = 0
    for failed_challenge in failed_challenges:
        # Recalculate streak information for failed challenges
        failed_challenge.calculate_streak_before_failure()
        failed_updated_count += 1

    return f"Updated {updated_count} user challenge streaks and {super_updated_count} super challenge streaks. {super_failed_count} super challenges failed. Updated {failed_updated_count} previously failed challenges."
