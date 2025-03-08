from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.main.models import UserTournament
from apps.notification.models import Notification, NotificationTemplate
from apps.telegram_bot.utils import send_broadcast


@receiver(post_save, sender=UserTournament)
def handle_tournament_failure(sender, instance, created, **kwargs):
    """
    Handle tournament failure notifications when a UserTournament is marked as failed
    """
    if not created and instance.is_failed:
        # Get the failure notification template for this tournament
        template = NotificationTemplate.objects.filter(
            type="tournament_failed", tournament=instance.tournament
        ).first()

        if template:
            # Create notification
            notification = Notification.objects.create(
                template=template, user=instance.user
            )

            # Send telegram notification if user has telegram_id
            if instance.user.telegram_id:
                send_broadcast(
                    user_id=instance.user.telegram_id, message=template.message
                )
