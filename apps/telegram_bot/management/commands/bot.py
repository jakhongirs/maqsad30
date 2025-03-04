from django.conf import settings
from django.core.management.base import BaseCommand
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from apps.users.models import Timezone, User

TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
WEB_APP_URL = settings.WEB_APP_URL
CHANNEL_ID = "-1002128930156"

# Member status constants
MEMBER_STATUSES = ["member", "administrator", "creator"]


async def check_channel_membership(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Check if user is a member of the required channel."""
    try:
        chat_member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID, user_id=update.effective_user.id
        )
        return chat_member.status in MEMBER_STATUSES
    except TelegramError:
        return False


async def create_or_update_user(user) -> User:
    """Create or update user from Telegram data."""
    # Generate a unique username if needed
    base_username = user.username or f"user_{user.id}"
    username = base_username
    suffix = 1

    # Keep trying with different suffixes until we find a unique username
    while User.objects.filter(username=username).exists():
        username = f"{base_username}_{suffix}"
        suffix += 1

    # Create or update user
    user_obj, created = User.objects.update_or_create(
        telegram_id=str(user.id),
        defaults={
            "username": username,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "telegram_username": user.username,
            "telegram_photo_url": (
                user.get_profile_photos().photos[0][-1].file_url
                if user.get_profile_photos().total_count > 0
                else None
            ),
        },
    )

    # Set default timezone if not set
    if not user_obj.timezone:
        timezone, _ = Timezone.objects.get_or_create(
            name="Asia/Tashkent", defaults={"offset": "+05:00"}
        )
        user_obj.timezone = timezone
        user_obj.save(update_fields=["timezone"])

    return user_obj


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    is_member = await check_channel_membership(update, context)

    if not is_member:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="📢 Kanaga a'zo bo'lish",
                        url="https://t.me/+67Qw_YtRsLgxOTMy",
                    )
                ]
            ]
        )

        await update.message.reply_text(
            "📢 *Botdan foydalanish uchun avval kanalimizga a'zo bo'ling!*",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Only create user if they don't exist
    if not User.objects.filter(telegram_id=str(update.effective_user.id)).exists():
        await create_or_update_user(update.effective_user)

    # If user is a member, show welcome message with web app button
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="Kirish", web_app=WebAppInfo(url=WEB_APP_URL))]]
    )

    await update.message.reply_text(
        "*Maqsad Club botiga xush kelibsiz!*",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )


class Command(BaseCommand):
    help = "Starts the Telegram bot"

    def handle(self, *args, **options):
        # Build and configure the application
        application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start))

        # Start the bot
        self.stdout.write(self.style.SUCCESS("Bot started"))
        application.run_polling()
