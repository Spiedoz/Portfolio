import sqlite3
from telegram import Update
from telegram.ext import ContextTypes
from bot.core import admin

bot_admin = admin()

async def restorationGuild(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """useful to remove guilds when unexpected things happen"""
    if update.message.from_user.id in bot_admin:
        conn = sqlite3.connect("dungeon.db")
        c = conn.cursor()
        try:
            guild = update.message.text.split(' ', 1)[1]
        except:
            return
        g = c.execute("SELECT COUNT(*) FROM Guild WHERE name = ?",(guild,)).fetchone()[0]
        if g == 0:
            c.execute("DELETE FROM Guilds WHERE nome = ?", (guild,))
        conn.commit()
        conn.close()
        text = "Guild deleted successfully!"
        await update.message.reply_text(parse_mode= 'HTML', text= text)

async def players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """return count of the player registered in the bot"""
    if update.message.from_user.id in bot_admin:
        conn = sqlite3.connect("dungeon.db")
        c = conn.cursor()
        num_users = c.execute("SELECT COUNT(user_id) FROM Profile").fetchone()[0]
        text = "Amount of registered players: <b>" + str(num_users) + "</b>"
        await update.message.reply_text(parse_mode= 'HTML', text= text)
        conn.commit()
        conn.close()

async def addGold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """increases the money of the user to whom the message is responded to"""
    if update.message.from_user.id in bot_admin:
        conn = sqlite3.connect('dungeon.db')
        c = conn.cursor()
        if update.message.reply_to_message.message_id:
            try:
                gold = int(update.message.text.split(' ', 1)[1])
                target_user_id = update.message.reply_to_message.from_user.id
            except:
                return
        c.execute("UPDATE User SET gold = (SELECT gold FROM User WHERE user_id = ?)+? WHERE user_id = ?;", (target_user_id, gold, target_user_id))
        nicknameTarget = c.execute("SELECT nickname FROM User WHERE user_id = ?", (target_user_id,)).fetchone()[0]
        await update.message.reply_text(parse_mode= 'HTML', text= "Added " + "<b>" + str(gold) + " gold</b> to: " + nicknameTarget)
        conn.commit()
        conn.close()


async def addLvl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """increases the level of the user to whom the message is responded to"""
    if update.message.from_user.id in bot_admin:
        conn = sqlite3.connect('dungeon.db')
        c = conn.cursor()
        if update.message.reply_to_message.message_id:
            try:
                lvl = int(update.message.text.split(' ', 1)[1])
                target_user_id = update.message.reply_to_message.from_user.id
            except:
                return
        c.execute("UPDATE User SET lvl = (SELECT lvl FROM User WHERE user_id = ?)+? WHERE user_id = ?;",
                  (target_user_id, lvl, target_user_id))
        nicknameTarget = c.execute("SELECT nickname FROM User WHERE user_id = ?", (target_user_id,)).fetchone()[0]
        stats = 3 * int(lvl)
        c.execute(
            "UPDATE Profile SET stats_points = (SELECT stats_points FROM Profile WHERE user_id = ?)+? WHERE user_id = ?",
            (target_user_id, stats, target_user_id,))
        await context.bot.send_message(chat_id=update.effective_message.chat.id, parse_mode='HTML',
                                       text="Someone here feels much stronger now! (" + "<b>" + str(
                                           lvl) + " Lvl/s)</b>\nNice one, " + nicknameTarget)
        conn.commit()
        conn.close()


async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """punish players, avoiding them to use the bot"""
    if update.message.from_user.id in bot_admin:
        conn = sqlite3.connect('dungeon.db')
        c = conn.cursor()
        try:
            nickname = update.message.text.split(' ', 1)[1]
        except:
            return
        if c.execute("SELECT * FROM User WHERE nickname = ?", (nickname,)).fetchall():
            user_id = c.execute("SELECT user_id FROM User WHERE nickname = ?", (nickname,)).fetchone()[0]
            if c.execute("SELECT COUNT(*) FROM Ban WHERE user_id = ?", (user_id,)).fetchone()[0] == 0:
                c.execute("DELETE FROM Inventory WHERE user_id = ?", (user_id,))
                c.execute("DELETE FROM Profile WHERE user_id = ?", (user_id,))
                c.execute("DELETE FROM Guild WHERE user_id = ?", (user_id,))
                c.execute("DELETE FROM Equipment WHERE user_id = ?", (user_id,))
                c.execute("DELETE FROM User WHERE user_id = ?", (user_id,))
                c.execute("DELETE FROM Nickname WHERE user_id = ?", (user_id,))
                c.execute("DELETE FROM Messages WHERE user_id = ?", (user_id,))
                c.execute("INSERT INTO BAN(user_id) VALUES(?)", (user_id,))
                text = nickname + " was banned."
                await update.message.reply_text(parse_mode='HTML', text=text)
            else:
                text = "This player is already banned!"
                await update.message.reply_text(parse_mode='HTML', text=text)
        else:
            text = "This player does not exist."
            await update.message.reply_text(parse_mode='HTML', text=text)
        conn.commit()
        conn.close()


async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """remove the user banned from the ban list"""
    if update.message.from_user.id in bot_admin:
        conn = sqlite3.connect("dungeon.db")
        c = conn.cursor()
        if update.message.reply_to_message.message_id:
            try:
                target_user_id = update.message.reply_to_message.from_user.id
            except:
                return
        if c.execute("SELECT COUNT(*) FROM Ban WHERE user_id = ?", (target_user_id,)).fetchone()[0] == 0:
            text = "This player is not banned!"
            await update.message.reply_text(parse_mode='HTML', text=text)
        else:
            c.execute("DELETE FROM Ban WHERE user_id = ?", (target_user_id,))
            text = "Player unbanned."
            await update.message.reply_text(parse_mode='HTML', text=text)
        conn.commit()
        conn.close()


async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """function useful to announce something to every user registered"""
    if update.message.from_user.id in bot_admin:
        conn = sqlite3.connect("dungeon.db")
        c = conn.cursor()
        try:
            message = update.message.text.split(' ', 1)[1]
        except:
            return
        user = c.execute("SELECT user_id FROM User").fetchall()
        for users in user:
            chat_id = c.execute("SELECT chat_id FROM User WHERE user_id = ? ",(users[0],)).fetchone()[0]
            await context.bot.send_message(chat_id= chat_id, parse_mode = 'HTML', text= message)
        conn.commit()
        conn.close()