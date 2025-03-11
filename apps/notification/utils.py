import asyncio
import logging

from django.utils import timezone

from apps.notification.models import (
    ChallengeNotificationTemplate,
    NotificationLog,
    SuperChallengeNotificationTemplate,
)
from apps.telegram_bot.models import CustomMessage
from apps.telegram_bot.utils import send_broadcast

logger = logging.getLogger(__name__)


def create_temp_message(title, message_text, is_attach_link=False):
    """
    Create a temporary CustomMessage object for use with send_broadcast.

    Args:
        title (str): Message title
        message_text (str): Message text
        is_attach_link (bool): Whether to attach a link to the message

    Returns:
        CustomMessage: A non-persisted CustomMessage object
    """
    message = CustomMessage(
        title=title, message=message_text, is_attach_link=is_attach_link
    )
    return message


def send_challenge_notification(user_challenge):
    """
    Send a notification for a challenge to a user.

    Args:
        user_challenge (UserChallenge): User challenge object

    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    user = user_challenge.user
    challenge = user_challenge.challenge

    # Skip if user doesn't have a Telegram ID
    if not user.telegram_id:
        return False

    # Get notification template
    try:
        template = ChallengeNotificationTemplate.objects.get(
            challenge=challenge, is_active=True
        )
    except ChallengeNotificationTemplate.DoesNotExist:
        logger.warning(f"No active notification template for challenge {challenge.id}")
        return False

    # Create notification log
    notification_log = NotificationLog.objects.create(
        user=user,
        challenge=challenge,
        message=template.message,
        notification_type="challenge",
    )

    # Create temporary message object
    temp_message = create_temp_message(
        title=challenge.title, message_text=template.message, is_attach_link=False
    )

    # Send notification
    try:
        asyncio.run(send_broadcast(user.telegram_id, temp_message))
        notification_log.is_sent = True
        notification_log.save()
        return True
    except Exception as e:
        notification_log.error_message = str(e)
        notification_log.save()
        logger.error(f"Error sending challenge notification: {str(e)}")
        return False


def send_super_challenge_general_notification(user_super_challenge):
    """
    Send a general notification for a super challenge to a user.

    Args:
        user_super_challenge (UserSuperChallenge): User super challenge object

    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    user = user_super_challenge.user
    super_challenge = user_super_challenge.super_challenge

    # Skip if user doesn't have a Telegram ID
    if not user.telegram_id:
        return False

    # Skip if user has failed the super challenge
    if user_super_challenge.is_failed:
        return False

    # Get notification template
    try:
        template = SuperChallengeNotificationTemplate.objects.get(
            super_challenge=super_challenge, is_active=True
        )
    except SuperChallengeNotificationTemplate.DoesNotExist:
        logger.warning(
            f"No active notification template for super challenge {super_challenge.id}"
        )
        return False

    # Check if we should send this type of notification today
    notification_type = "super_challenge_general"
    if not should_send_super_challenge_notification(
        user_super_challenge, notification_type
    ):
        logger.info(
            f"Skipping {notification_type} notification for user {user.id} - already sent today"
        )
        return False

    # Create notification log
    notification_log = NotificationLog.objects.create(
        user=user,
        super_challenge=super_challenge,
        message=template.general_message,
        notification_type=notification_type,
    )

    # Create temporary message object
    temp_message = create_temp_message(
        title=super_challenge.title,
        message_text=template.general_message,
        is_attach_link=False,
    )

    # Send notification
    try:
        asyncio.run(send_broadcast(user.telegram_id, temp_message))
        notification_log.is_sent = True
        notification_log.save()
        return True
    except Exception as e:
        notification_log.error_message = str(e)
        notification_log.save()
        logger.error(f"Error sending super challenge general notification: {str(e)}")
        return False


def send_super_challenge_progress_notification(user_super_challenge):
    """
    Send a progress notification for a super challenge to a user.
    This is sent when a user hasn't completed all challenges for the day.

    Args:
        user_super_challenge (UserSuperChallenge): User super challenge object

    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    user = user_super_challenge.user
    super_challenge = user_super_challenge.super_challenge

    # Skip if user doesn't have a Telegram ID
    if not user.telegram_id:
        return False

    # Get notification template
    try:
        template = SuperChallengeNotificationTemplate.objects.get(
            super_challenge=super_challenge, is_active=True
        )
    except SuperChallengeNotificationTemplate.DoesNotExist:
        logger.warning(
            f"No active notification template for super challenge {super_challenge.id}"
        )
        return False

    # Get current date and previous date
    current_date = timezone.localtime().date()
    previous_date = current_date - timezone.timedelta(days=1)

    # Determine which message to send based on failure status
    if user_super_challenge.is_failed:
        message = template.failure_message
        notification_type = "super_challenge_failure"
    else:
        # Check if the user completed the challenge on the previous day
        # If they did, we don't need to send a warning message
        if user_super_challenge.is_completed_for_date(previous_date):
            logger.info(
                f"Skipping warning notification for user {user.id} - completed super challenge yesterday"
            )
            return False

        message = template.progress_warning_message
        notification_type = "super_challenge_warning"

    # Check if we should send this type of notification today
    if not should_send_super_challenge_notification(
        user_super_challenge, notification_type
    ):
        logger.info(
            f"Skipping {notification_type} notification for user {user.id} - already sent today"
        )
        return False

    # Create notification log
    notification_log = NotificationLog.objects.create(
        user=user,
        super_challenge=super_challenge,
        message=message,
        notification_type=notification_type,
    )

    # Create temporary message object
    temp_message = create_temp_message(
        title=super_challenge.title, message_text=message, is_attach_link=False
    )

    # Send notification
    try:
        asyncio.run(send_broadcast(user.telegram_id, temp_message))
        notification_log.is_sent = True
        notification_log.save()
        return True
    except Exception as e:
        notification_log.error_message = str(e)
        notification_log.save()
        logger.error(f"Error sending super challenge progress notification: {str(e)}")
        return False


def should_send_challenge_notification(user_challenge):
    """
    Check if a challenge notification should be sent.

    Args:
        user_challenge (UserChallenge): User challenge object

    Returns:
        bool: Always returns True since notifications are now scheduled at exact times
    """
    # Since we're scheduling the task to run exactly at challenge start times (19:00 and 20:00),
    # we don't need to check the time difference anymore
    return True


def should_send_super_challenge_notification(
    user_super_challenge, notification_type="super_challenge_general"
):
    """
    Check if a super challenge notification should be sent.

    Args:
        user_super_challenge (UserSuperChallenge): User super challenge object
        notification_type (str): Type of notification to check for
            (super_challenge_general, super_challenge_warning, super_challenge_failure)

    Returns:
        bool: True if notification should be sent, False otherwise
    """
    # Get current date and time
    now = timezone.localtime()
    current_date = now.date()
    previous_date = current_date - timezone.timedelta(days=1)

    # Check if super challenge is active for the current date or was active for the previous date
    super_challenge = user_super_challenge.super_challenge

    # For progress notifications (warnings and failures), we need to check if the challenge
    # was active yesterday, since we're checking for yesterday's completions
    if notification_type in ["super_challenge_warning", "super_challenge_failure"]:
        if not (
            super_challenge.start_date <= previous_date <= super_challenge.end_date
        ):
            return False
    else:
        # For general notifications, check if the challenge is active today
        if not (super_challenge.start_date <= current_date <= super_challenge.end_date):
            return False

    # Check if notification of this specific type has already been sent today
    already_sent = NotificationLog.objects.filter(
        user=user_super_challenge.user,
        super_challenge=super_challenge,
        notification_type=notification_type,
        sent_at__date=current_date,
        is_sent=True,
    ).exists()

    return not already_sent
