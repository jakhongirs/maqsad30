from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.main.models import Challenge, ChallengeAward, UserAward, UserChallenge


@receiver(post_save, sender=Challenge)
def create_challenge_award(sender, instance, created, **kwargs):
    if created:
        ChallengeAward.objects.get_or_create(challenge=instance)


@receiver(post_save, sender=UserChallenge)
def check_and_award_user(sender, instance, **kwargs):
    if instance.highest_streak >= 30:
        # Try to create the award for the user if they don't have it already
        UserAward.objects.get_or_create(
            user=instance.user, award=instance.challenge.award
        )
