from celery import shared_task
from django.utils import timezone

from apps.main.models import UserChallenge, UserTournament, UserTournamentDay
from apps.notification.models import Notification, NotificationTemplate
from apps.telegram_bot.utils import send_broadcast


@shared_task
def send_challenge_notifications():
    """Send notifications for challenges at their start time"""
    current_time = timezone.localtime().time()

    # Get all challenge templates that should send notifications now
    templates = NotificationTemplate.objects.filter(
        type="challenge_reminder",
        challenge__start_time=current_time,
    ).select_related("challenge")

    for template in templates:
        # Get all users who have this challenge
        user_challenges = UserChallenge.objects.filter(
            challenge=template.challenge
        ).select_related("user")

        for user_challenge in user_challenges:
            # Create notification
            notification = Notification.objects.create(
                template=template, user=user_challenge.user
            )

            # Send telegram notification if user has telegram_id
            if user_challenge.user.telegram_id:
                send_broadcast(
                    user_id=user_challenge.user.telegram_id, message=template.message
                )


@shared_task
def send_tournament_daily_notifications():
    """Send daily notifications for tournaments"""
    current_time = timezone.localtime().time()
    current_date = timezone.localtime().date()

    # Get all tournament templates for daily reminders
    templates = NotificationTemplate.objects.filter(
        type="tournament_daily",
    ).select_related("tournament")

    for template in templates:
        # Get all active user tournaments for this tournament
        user_tournaments = UserTournament.objects.filter(
            tournament=template.tournament,
            is_failed=False,
        ).select_related("user")

        for user_tournament in user_tournaments:
            # Check if user has completed today's challenges
            day_record = UserTournamentDay.objects.filter(
                user_tournament=user_tournament,
                date=current_date,
            ).first()

            if day_record and not day_record.is_completed:
                # Create notification
                notification = Notification.objects.create(
                    template=template, user=user_tournament.user
                )

                # Send telegram notification if user has telegram_id
                if user_tournament.user.telegram_id:
                    send_broadcast(
                        user_id=user_tournament.user.telegram_id,
                        message=template.message,
                    )


@shared_task
def send_tournament_missed_notifications():
    """Send notifications when user misses a tournament day"""
    current_date = timezone.localtime().date()

    # Get all tournament templates for missed notifications
    templates = NotificationTemplate.objects.filter(
        type="tournament_missed",
    ).select_related("tournament")

    for template in templates:
        # Get all active user tournaments for this tournament
        user_tournaments = UserTournament.objects.filter(
            tournament=template.tournament,
            is_failed=False,
        ).select_related("user")

        for user_tournament in user_tournaments:
            # Check if user missed yesterday's challenges
            yesterday = current_date - timezone.timedelta(days=1)
            day_record = UserTournamentDay.objects.filter(
                user_tournament=user_tournament,
                date=yesterday,
            ).first()

            if day_record and not day_record.is_completed:
                # Create notification
                notification = Notification.objects.create(
                    template=template, user=user_tournament.user
                )

                # Send telegram notification if user has telegram_id
                if user_tournament.user.telegram_id:
                    send_broadcast(
                        user_id=user_tournament.user.telegram_id,
                        message=template.message,
                    )


@shared_task
def send_tournament_failed_notifications():
    """Send notifications when user fails a tournament"""
    # Get all tournament templates for failure notifications
    templates = NotificationTemplate.objects.filter(
        type="tournament_failed",
    ).select_related("tournament")

    for template in templates:
        # Get all user tournaments that just failed
        user_tournaments = UserTournament.objects.filter(
            tournament=template.tournament,
            is_failed=True,
            # We'll use updated_at to check if the failure just happened
            updated_at__gte=timezone.now() - timezone.timedelta(minutes=5),
        ).select_related("user")

        for user_tournament in user_tournaments:
            # Create notification
            notification = Notification.objects.create(
                template=template, user=user_tournament.user
            )

            # Send telegram notification if user has telegram_id
            if user_tournament.user.telegram_id:
                send_broadcast(
                    user_id=user_tournament.user.telegram_id, message=template.message
                )
