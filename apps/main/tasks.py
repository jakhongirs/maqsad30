import logging

from celery import shared_task
from django.utils import timezone

from apps.main.models import (
    Tournament,
    TournamentAward,
    UserAward,
    UserChallenge,
    UserTournament,
)

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


@shared_task
def process_tournament_day_end():
    """
    Process tournament day completions for the previous day.
    This task should be scheduled to run after the end time of the last challenge of the day.
    """
    current_time = timezone.localtime()
    yesterday = current_time.date() - timezone.timedelta(days=1)

    logger.info(
        f"Processing tournament day end for date: {yesterday} (executed at {current_time})"
    )

    try:
        UserTournament.process_day_end(yesterday)
        logger.info(f"Successfully processed tournament day end for {yesterday}")
    except Exception as e:
        logger.error(f"Error processing tournament day end: {str(e)}")
        raise


@shared_task
def process_tournament_awards():
    """
    Process awards for finished tournaments and deactivate them.
    This task handles both creating awards for successful participants and deactivating finished tournaments.
    """
    now = timezone.localtime()
    logger.info(f"Processing tournament awards at: {now}")

    try:
        # Get finished tournaments that are still active
        finished_tournaments = Tournament.objects.filter(
            finish_date__lte=now, is_active=True
        )

        for tournament in finished_tournaments:
            # Create tournament award if it doesn't exist
            tournament_award, _ = TournamentAward.objects.get_or_create(
                tournament=tournament
            )

            # Get all user tournaments that were not failed
            successful_user_tournaments = UserTournament.objects.filter(
                tournament=tournament, is_failed=False
            )

            # Create awards for successful users
            for user_tournament in successful_user_tournaments:
                UserAward.objects.get_or_create(
                    user=user_tournament.user, tournament_award=tournament_award
                )

            # Mark tournament as inactive after processing
            tournament.is_active = False
            tournament.save()
            logger.info(
                f"Processed awards and deactivated tournament: {tournament.title}"
            )

        return f"Successfully processed awards for {finished_tournaments.count()} tournaments"
    except Exception as e:
        logger.error(f"Error processing tournament awards: {str(e)}")
        raise
