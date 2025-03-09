import asyncio

from celery import shared_task
from django.utils import timezone

from apps.main.models import UserChallenge
from apps.telegram_bot.models import CustomMessage
from apps.telegram_bot.utils import send_broadcast
from apps.users.models import User


@shared_task
def async_send_message_to_users(message_id):
    message = CustomMessage.objects.get(id=message_id)

    # Base query to get users with telegram IDs
    users = User.objects.exclude(telegram_id__isnull=True).exclude(telegram_id="")

    # If message is associated with a challenge, filter users who have access to it
    if message.challenge:
        user_ids_with_challenge = UserChallenge.objects.filter(
            challenge=message.challenge
        ).values_list("user_id", flat=True)
        users = users.filter(id__in=user_ids_with_challenge)

    print(f"Sending message to {len(users)} users")

    async def send_notifications():
        for user in users:
            await send_broadcast(user_id=user.telegram_id, message=message)

    asyncio.run(send_notifications())
    message.sent = True
    message.sent_at = timezone.now()
    message.save()
