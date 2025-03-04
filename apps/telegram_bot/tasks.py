import asyncio

from celery import shared_task
from django.utils import timezone

from apps.telegram_bot.models import CustomMessage
from apps.telegram_bot.utils import send_broadcast
from apps.users.models import User


@shared_task
def async_send_message_to_users(message_id):
    message = CustomMessage.objects.get(id=message_id)
    users = (
        User.objects.filter(id__in=[3017, 2988, 2770, 883])
        .exclude(telegram_id__isnull=True)
        .exclude(telegram_id="")
    )

    print(len(users))

    async def send_notifications():
        for user in users:
            await send_broadcast(user_id=user.telegram_id, message=message)

    asyncio.run(send_notifications())
    message.sent = True
    message.sent_at = timezone.now()
    message.save()
