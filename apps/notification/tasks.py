import logging

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from apps.main.models import UserChallenge, UserSuperChallenge
from apps.notification.utils import (
    send_challenge_notification,
    send_super_challenge_general_notification,
    send_super_challenge_progress_notification,
    should_send_challenge_notification,
)

logger = logging.getLogger(__name__)


@shared_task
def send_challenge_notifications():
    """
    Send notifications for all active challenges.
    This task is scheduled to run at specific times (05:00, 19:00 and 20:00).
    It will only send notifications for challenges that start at the current hour.
    """
    logger.info("Starting challenge notification task")

    # Get current hour
    current_hour = timezone.localtime().hour

    # Map scheduled task hours to challenge start times
    # This handles the case where the task runs at 21:00 but we want to notify for 20:00 challenges
    notification_hour_mapping = {
        5: 5,  # 05:00 task notifies for 05:00 challenges
        19: 19,  # 19:00 task notifies for 19:00 challenges
        20: 20,  # 20:00 task notifies for 20:00 challenges
    }

    # Get the target hour for challenge start times
    target_hour = notification_hour_mapping.get(current_hour)

    if target_hour is None:
        logger.warning(f"No target hour mapping for current hour {current_hour}")
        return 0

    logger.info(f"Sending notifications for challenges starting at {target_hour}:00")

    # Get all active user challenges with the matching start time hour
    user_challenges = UserChallenge.objects.filter(
        is_active=True,
        challenge__notification_template__is_active=True,
        challenge__start_time__hour=target_hour,
    ).select_related("user", "challenge", "challenge__notification_template")

    sent_count = 0
    for user_challenge in user_challenges:
        if should_send_challenge_notification(user_challenge):
            success = send_challenge_notification(user_challenge)
            if success:
                sent_count += 1

    logger.info(
        f"Sent {sent_count} challenge notifications for {target_hour}:00 challenges"
    )
    return sent_count


@shared_task
def send_super_challenge_general_notifications():
    """
    Send general notifications for all active super challenges.
    This task should be scheduled to run once a day at a specific time.
    """
    logger.info("Starting super challenge general notification task")

    # Get current date
    current_date = timezone.localtime().date()

    # Get all active user super challenges
    user_super_challenges = UserSuperChallenge.objects.filter(
        is_active=True,
        is_failed=False,
        super_challenge__notification_template__is_active=True,
        super_challenge__start_date__lte=current_date,
        super_challenge__end_date__gte=current_date,
    ).select_related(
        "user", "super_challenge", "super_challenge__notification_template"
    )

    sent_count = 0
    for user_super_challenge in user_super_challenges:
        success = send_super_challenge_general_notification(user_super_challenge)
        if success:
            sent_count += 1

    logger.info(f"Sent {sent_count} super challenge general notifications")
    return sent_count


@shared_task
def send_super_challenge_progress_notifications():
    """
    Send progress notifications for super challenges.
    This task should be scheduled to run once a day after the completion deadline.
    """
    logger.info("Starting super challenge progress notification task")

    # Get current date and previous date
    current_date = timezone.localtime().date()
    previous_date = current_date - timezone.timedelta(days=1)

    # Get all active user super challenges
    user_super_challenges = UserSuperChallenge.objects.filter(
        Q(is_active=True) | Q(is_failed=True),
        super_challenge__notification_template__is_active=True,
        super_challenge__start_date__lte=previous_date,
        super_challenge__end_date__gte=previous_date,
    ).select_related(
        "user", "super_challenge", "super_challenge__notification_template"
    )

    sent_count = 0
    for user_super_challenge in user_super_challenges:
        # Check if user completed all challenges yesterday
        # We'll need to modify the is_completed_today method to accept a date parameter
        if not user_super_challenge.is_completed_for_date(previous_date):
            # Send progress notification
            success = send_super_challenge_progress_notification(user_super_challenge)
            if success:
                sent_count += 1

    logger.info(f"Sent {sent_count} super challenge progress notifications")
    return sent_count
