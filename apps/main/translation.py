from modeltranslation.translator import TranslationOptions, register

from .models import Challenge, Tournament


@register(Challenge)
class ChallengeTranslationOptions(TranslationOptions):
    fields = ("title", "rules")


@register(Tournament)
class TournamentTranslationOptions(TranslationOptions):
    fields = ("title",)
