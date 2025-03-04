from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.telegram_bot.models import CustomMessage
from apps.telegram_bot.tasks import async_send_message_to_users


@receiver(post_save, sender=CustomMessage)
def send_announcement_to_users(sender, instance, created, **kwargs):
    if created:
        # countdown=10 means the task will be executed after 10 seconds delay
        async_send_message_to_users.apply_async((instance.id,), countdown=10)
