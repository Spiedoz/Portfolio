import telegram
import sqlite3
from telegram import Update
from telegram.ext import ContextTypes


# Banned / Unregistered Players
async def user_registered(update: Update) -> bool:
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM User WHERE user_id = ?",
                 (str(update.effective_message.from_user.id),)).fetchone()[0] == 0:
        conn.commit()
        conn.close()
        return False
    else:
        return True


async def user_banned(update: Update) -> bool:
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM Ban WHERE user_id = ?",
                 (update.effective_message.from_user.id,)).fetchone()[0] == 0:
        conn.commit()
        conn.close()
        return False
    else:
        return True


async def warning_unregistered_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "You can't do anything if you aren't registered!"
    await context.bot.send_message(chat_id=update.effective_chat.id, parse_mode='HTML', text=text)


async def user_is_battling(update: Update) -> bool:
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    if c.execute("SELECT status FROM Profile WHERE user_id = ?",
                 (str(update.effective_message.from_user.id),)).fetchone()[0] == 'in_battle':
        conn.commit()
        conn.close()
        return True
    else:
        return False


async def user_is_trading(update: Update) -> bool:
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    if c.execute("SELECT status FROM Profile WHERE user_id = ?",
                 (str(update.effective_message.from_user.id),)).fetchone()[0] == 'trading':
        conn.commit()
        conn.close()
        return True
    else:
        return False

async def warning_battling_user(update : Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "You are currently in a battle!"
    await context.bot.send_message(chat_id=update.effective_chat.id, parse_mode='HTML', text=text)


async def warning_trading_user(update : Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "You are currently in a trade!"
    await context.bot.send_message(chat_id=update.effective_chat.id, parse_mode='HTML', text=text)


# Type of Chat
async def check_chat(update: Update) -> bool:
    if update.message.chat.type == 'group' or update.message.chat.type == 'supergroup':
        return True
    else:
        return False


async def warning_chat(update: Update) -> None:
    await update.message.reply_text(text="This command can only be used in private!")


# Location Player
async def warning_safe(update: Update) -> None:
    text = "You can't use this command in a safe zone!"
    armory = telegram.KeyboardButton(text="/armory")
    tavern = telegram.KeyboardButton(text="/tavern")
    travel = telegram.KeyboardButton(text="/travel")
    explore = telegram.KeyboardButton(text="/explore")
    reply_markup0 = telegram.ReplyKeyboardMarkup(keyboard=[[armory, tavern], [travel, explore]],
                                                 resize_keyboard=True, selective=True)
    await update.message.reply_text(text=text, reply_markup=reply_markup0)

async def warning_unsafe(update: Update) -> None:
    text = "You can't use this command in an unsafe area!"
    await update.message.reply_text(text=text)