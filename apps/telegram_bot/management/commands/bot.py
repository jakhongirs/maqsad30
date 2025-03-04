from asgiref.sync import sync_to_async
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


async def get_user_photo_url(user) -> str | None:
    """Get user's profile photo URL."""
    try:
        photos = await user.get_profile_photos()
        if photos.total_count > 0:
            # Get the first photo (most recent) and its largest size
            photo = photos.photos[0][-1]
            # Get the direct file URL through the bot API
            file = await photo.get_file()
            return file.file_path
    except Exception as e:
        print(f"Error getting photo URL: {e}")
    return None


@sync_to_async
def check_user_exists(telegram_id: str) -> bool:
    """Check if user exists in database."""
    return User.objects.filter(telegram_id=telegram_id).exists()


@sync_to_async
def create_user_sync(user_data: dict) -> User:
    """Create user from data dictionary."""
    # Generate a unique username if needed
    base_username = user_data["username"] or f"user_{user_data['telegram_id']}"
    username = base_username
    suffix = 1

    # Keep trying with different suffixes until we find a unique username
    while User.objects.filter(username=username).exists():
        username = f"{base_username}_{suffix}"
        suffix += 1

    # Create user
    user_obj = User.objects.create(
        telegram_id=user_data["telegram_id"],
        username=username,
        first_name=user_data["first_name"] or "",
        last_name=user_data["last_name"] or "",
        telegram_username=user_data["username"],
        telegram_photo_url=user_data["photo_url"],
    )

    # Set default timezone
    timezone, _ = Timezone.objects.get_or_create(
        name="Asia/Tashkent", defaults={"offset": "+05:00"}
    )
    user_obj.timezone = timezone
    user_obj.save(update_fields=["timezone"])

    return user_obj


async def create_user(user) -> User:
    """Create user with async photo fetching."""
    # Get photo URL asynchronously
    photo_url = await get_user_photo_url(user)

    # Prepare user data
    user_data = {
        "telegram_id": str(user.id),
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "photo_url": photo_url,
    }

    # Create user in database
    return await create_user_sync(user_data)


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
    user_exists = await check_user_exists(str(update.effective_user.id))
    if not user_exists:
        await create_user(update.effective_user)

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
