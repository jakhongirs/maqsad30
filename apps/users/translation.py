from modeltranslation.translator import TranslationOptions, register

from apps.users.models import Timezone


@register(Timezone)
class TimezoneTranslationOptions(TranslationOptions):
    fields = ("name",)
