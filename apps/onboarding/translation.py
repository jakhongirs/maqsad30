from modeltranslation.translator import TranslationOptions, register

from .models import FAQ, Answer, Question


@register(Question)
class QuestionTranslationOptions(TranslationOptions):
    fields = ("title",)


@register(Answer)
class AnswerTranslationOptions(TranslationOptions):
    fields = ("text",)


@register(FAQ)
class FAQTranslationOptions(TranslationOptions):
    fields = ("question", "answer")
