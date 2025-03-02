from django.core.management.base import BaseCommand
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_BOT_TOKEN = "7217412861:AAEq1F5tHwiSLqtDMqccFTNarlFYl4xdzX0"
WEB_APP_URL = "https://maqsad30.icc-kimyo.uz/"
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    is_member = await check_channel_membership(update, context)

    if not is_member:
        # If the user is not a member of the channel, send an invite link
        invite_link = f"https://t.me/{CHANNEL_ID[1:]}"  # Remove the leading '-' for the channel link
        await update.message.reply_text(
            f"*Maqsad Club botiga xush kelibsiz!*\n\n"
            f"Avvalo, kanalimizga qo'shiling: [Join Channel]({invite_link})",
            reply_markup=None,
            parse_mode=ParseMode.MARKDOWN,
        )
        return

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
