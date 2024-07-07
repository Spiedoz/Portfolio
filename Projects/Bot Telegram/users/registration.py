import sqlite3
import re
from telegram.ext import ConversationHandler, ContextTypes
from telegram import Update
from utils.helpers import user_registered, user_banned, check_chat, warning_chat

from asset.asset import get_first_class

NICKNAME, CONFIRM_NICKNAME, INFOS = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks for the nickname."""

    if await check_chat(update):
        await warning_chat(update)
        return ConversationHandler.END

    if await user_registered(update):
        await update.message.reply_text(text= "You are already registered!")
        return ConversationHandler.END

    if await user_banned(update):
        return ConversationHandler.END

    text = ("Welcome adventurer to the <b>Reign of Mythic</b>.\n\n"
            "Before you pass through the gates to reach the <b>Main Square</b>, you must be registered in our records. "
            "You may state your name now..")
    await update.message.reply_text(text, parse_mode='HTML')

    return NICKNAME  # Return the state to proceed to getNickname


def starts_with_letter(nickname):
    """Checks if the given nickname starts with a letter (A-Z or a-z)
    and may contain special characters and spaces after the first letter."""
    pattern = r"^[A-Za-z][A-Za-z0-9 !@#$%^&*()_+=-]*$"
    match = re.match(pattern, nickname)
    return bool(match)


async def getNickname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the nickname in the database."""

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    user_id = update.effective_user.id
    nickname = update.message.text
    nicknames = c.execute("SELECT nickname FROM Nickname").fetchall()

    notLegit = True

    while notLegit:
        text = ""
        if len(nickname) > 10:
            text = ("Unfortunately this name is too long for us to register.\n"
                    "Please choose a name that is <b>not</b> longer than <b>10 characters</b>!")
        elif nickname in nicknames:
            text = "Unfortunately this name is already present in our records. Please choose another name!"
        elif not starts_with_letter(nickname):
            text = "This name doesn't seem real, can you choose one that starts with a <b>letter</b>?"

        if text:
            await update.message.reply_text(text= text, parse_mode="HTML")
            return NICKNAME  # Stay in the same state to retry nickname input

        notLegit = False

    if c.execute("SELECT COUNT(*) FROM Nickname WHERE user_id = ?", (user_id,)).fetchone()[0] == 0:
        c.execute("INSERT INTO Nickname (user_id, nickname) VALUES (?, ?)", (user_id, nickname,))
    else:
        c.execute("UPDATE Nickname SET nickname = ? WHERE user_id = ?", (nickname, user_id,))
    conn.commit()
    conn.close()

    text = f"Oh so you are <b>{nickname}.</b> Did I hear well?\n<i>(Yes / No)</i>"
    await update.message.reply_text(text, parse_mode='HTML')

    return CONFIRM_NICKNAME


async def confirm_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles user response to nickname confirmation."""

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    user_id = update.effective_user.id
    nickname = c.execute("SELECT nickname FROM Nickname WHERE user_id = ?", (user_id,)).fetchone()[0]

    answer = update.message.text.lower()
    if answer == "yes":
        text = (f"Good! You are now registered in our records. <b>{nickname}</b>, you may now proceed. "
                f"I'll show you around while explaining few things you need to know.\n\n"
                f"<i>(Write something to continue)</i>")
        await update.message.reply_text(text, parse_mode='HTML')
        return INFOS

    elif answer == "no":
        # Ask for a new nickname
        text = "Oh I'm sorry. Please repeat your name:"
        await update.message.reply_text(text)
        return NICKNAME  # Go back to nickname state

    else:
        # Invalid answer, prompt again
        text = "I didn't quite understand well. Please answer with a <b>Yes</b> or <b>No</b>."
        await update.message.reply_text(text= text, parse_mode="HTML")
        return CONFIRM_NICKNAME  # Stay in confirmation state


async def send_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ends the conversation and sends final instructions."""

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    user_id = update.effective_user.id
    nickname = c.execute("SELECT nickname FROM Nickname WHERE user_id = ?", (user_id,)).fetchone()[0]

    class_info = get_first_class()
    regionID = 1
    areaID = 1

    text = (
        f"● Here we are in the <b>Main Square</b>, here you can take advantage of the <b>tavern</b>'s facilities to rest from your adventures (/tavern).\n\n"
        f"● If, on the other hand, you want to strengthen yourself by buying weapons, you can visit our trusted <b>blacksmith</b> (/armory).\n\n"
        f"● You will begin your adventure as a <b>Trainee</b>!\n"
        f"Once you reach <b>level 10</b>, you can choose the path you prefer to take.\n\n"
        f"● If you need guidance or are lost, you can consult the guide with /guide.\n\n"
        f"The explanation is finished, you may now start your journey. Good luck out there, you'll <b>need</b> it!"
    )

    c.execute("DELETE FROM Nickname WHERE user_id = ?", (user_id,))

    c.execute("INSERT INTO Messages (user_id, nickname, num_msg) VALUES (?,?,?)", (user_id, nickname, 0))
    if c.execute("SELECT COUNT(*) FROM User WHERE user_id = ?", (user_id,)).fetchone()[0] == 0:
        c.execute("INSERT INTO User(user_id, chat_id, nickname, lvl, exp, gold, regionID, areaID, bounty) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, update.effective_message.chat.id, nickname, 1, 0, 25, regionID, areaID, 0))
    if c.execute("SELECT COUNT(*) FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0] == 0:
        c.execute("INSERT INTO Profile (user_id, class, status, hp, hp_max, hp_bonus, atk, atk_bonus, def, def_bonus, vel, vel_bonus, crit, stats_points) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(user_id), class_info[0], "idle", class_info[1], class_info[1], 0,
             class_info[2], 0, class_info[3], 0, class_info[4], 0, class_info[5], 0))

    conn.commit()
    conn.close()

    await update.message.reply_text(text, parse_mode='HTML')
    return ConversationHandler.END

async def command_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles command usage during a conversation."""

    await update.message.reply_text(
        text="❌ Commands are not allowed during a conversation. Please use regular messages.",
        parse_mode='HTML'
    )