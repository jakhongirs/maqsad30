import logging

import requests
from celery import shared_task
from django.conf import settings

from apps.users.models import User

logger = logging.getLogger(__name__)


@shared_task
def update_channel_membership_status():
    """
    Update Telegram channel membership status for all users.
    This task is scheduled to run once a day at midnight.
    Updates the status for each user based on their current channel membership.
    """
    logger.info("Starting channel membership status update task")

    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    channel_id = getattr(settings, "TELEGRAM_CHANNEL_ID", None)

    if not bot_token or not channel_id:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID is not configured")
        return 0

    # Get all users with telegram_id
    users = User.objects.filter(telegram_id__isnull=False)

    updated_count = 0
    url = f"https://api.telegram.org/bot{bot_token}/getChatMember"

    for user in users:
        try:
            params = {"chat_id": channel_id, "user_id": user.telegram_id}
            response = requests.get(url, params=params)
            data = response.json()

            is_member = False  # Default to False
            if "result" in data and "status" in data["result"]:
                member_status = data["result"]["status"]
                is_member = member_status in ["member", "administrator", "creator"]

            # Update status if it's different from current status
            if user.is_telegram_channel_member != is_member:
                user.is_telegram_channel_member = is_member
                user.save(update_fields=["is_telegram_channel_member"])
                updated_count += 1
                logger.info(
                    f"User {user.id} channel membership status updated to {is_member}"
                )

        except Exception as e:
            logger.error(f"Error checking channel membership for user {user.id}: {e}")
            continue

    logger.info(f"Updated channel membership status for {updated_count} users")
    return updated_count
