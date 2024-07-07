import logging
from telegram.ext import Application

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def init_bot():
    token = ""
    application = Application.builder().token(token).build()
    return application


def admin():
    bot_admin = []
    return bot_admin
