from django.conf import settings
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


async def send_broadcast(user_id, message):
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

    try:
        # Prepare message text based on title presence
        text = message.message
        if message.title:
            text = f"<b>{message.title}</b>\n\n{text}"

        keyboard = None
        # Only attach web app button if is_attach_link is True
        if message.is_attach_link and hasattr(settings, "WEB_APP_URL"):
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Kirish", web_app=WebAppInfo(url=settings.WEB_APP_URL)
                        )
                    ]
                ]
            )

        await bot.send_message(user_id, text, parse_mode="HTML", reply_markup=keyboard)

    except Exception as e:
        print(f"Error sending broadcast to member {user_id}: {str(e)}")
