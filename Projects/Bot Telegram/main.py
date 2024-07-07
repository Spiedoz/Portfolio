from telegram import Update
from bot.core import init_bot
from bot.handlers import register_handlers

if __name__ == "__main__":
    application = init_bot()

    register_handlers(application)
    application.run_polling(allowed_updates=Update.ALL_TYPES)
