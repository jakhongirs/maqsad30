from django.apps import AppConfig


class TelegramBotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.telegram_bot"

    def ready(self):
        import apps.telegram_bot.signals  # noqa
