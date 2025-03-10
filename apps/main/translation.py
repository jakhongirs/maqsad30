from modeltranslation.translator import TranslationOptions, register

from .models import Challenge


@register(Challenge)
class ChallengeTranslationOptions(TranslationOptions):
    fields = ("title", "rules")
