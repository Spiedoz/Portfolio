import sqlite3
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from utils.helpers import user_registered, user_banned, check_chat, warning_chat, warning_unregistered_user


async def guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """shows the guide to help users understand the features of the bot"""
    if not await user_registered(update):
        await warning_unregistered_user(update, context)
    else:
        if await check_chat(update):
            await warning_chat(update)
        else:
            if not await user_banned(update):
                text = ("Bot's Guide:\n\n(To put)")
                await update.message.reply_text(parse_mode= 'HTML', text= text)
            else:
                return


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """shows the top based on determined factors"""
    if not await user_registered(update):
        await warning_unregistered_user(update, context)
    else:
        if not await user_banned(update):
            buttonLvl = InlineKeyboardButton(text="Level", callback_data="lvl")
            buttonBounty = InlineKeyboardButton(text="Bounty", callback_data="bounty")
            buttonGuilds = InlineKeyboardButton(text="Guilds", callback_data="guilds")
            reply_markup = InlineKeyboardMarkup([[buttonLvl, buttonBounty, buttonGuilds]])

            await update.message.reply_text(
                text="Which top would you like to consult?",
                reply_markup=reply_markup
            )
        else:
            return


async def top_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage buttons of top function"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    query = update.callback_query
    cbd = update.callback_query.data
    buttonTop = telegram.InlineKeyboardButton(text='Back', callback_data='top')

    if cbd == 'lvl':
        text = "<b>Top Players:</b> <i>(Level)</i> \n\n"
        user = c.execute("SELECT nickname, user_id, lvl FROM User ORDER BY lvl DESC LIMIT 10").fetchall()
        i = 1
        for users in user:
            lvl = c.execute("SELECT lvl FROM User WHERE user_id = ? ", (users[1],)).fetchone()[0]
            text += str(i) + ') ' + users[0] + ' | ' + str(lvl) + ' \n'
            i += 1
        await query.edit_message_text(parse_mode='HTML', text=text,
                                      reply_markup=telegram.InlineKeyboardMarkup([[buttonTop]]))
    if cbd == 'bounty':
        text = "<b>Top Players:</b> <i>(Bounty)</i> \n\n"
        user = c.execute("SELECT nickname, user_id, bounty FROM User ORDER BY bounty DESC LIMIT 10").fetchall()
        i = 1
        for users in user:
            bounty = c.execute("SELECT bounty FROM User WHERE user_id = ? ", (users[1],)).fetchone()[0]
            text += str(i) + ') ' + users[0] + ' | ' + str(bounty) + ' \n'
            i += 1
        await query.edit_message_text(parse_mode='HTML', text=text,
                                      reply_markup=telegram.InlineKeyboardMarkup([[buttonTop]]))
    if cbd == 'guilds':
        text = "Top Guilds: <i>(Bounty)</i>\n\n"
        guilds = c.execute("SELECT name, bounty FROM Guilds ORDER BY bounty DESC LIMIT 10").fetchall()
        i = 1
        for guild in guilds:
            lvl = c.execute("SELECT bounty FROM Guilds WHERE name = ? ", (guild[0],)).fetchone()[0]
            text += str(i) + ') ' + guild[0] + ' | ' + str(lvl) + ' \n'
            i += 1
        await query.edit_message_text(parse_mode='HTML', text=text,
                                      reply_markup=telegram.InlineKeyboardMarkup([[buttonTop]]))
    if cbd == 'top':
        buttonLvl = telegram.InlineKeyboardButton(text='Level', callback_data='lvl')
        buttonBounty = telegram.InlineKeyboardButton(text='Bounty', callback_data='bounty')
        buttonGuilds = telegram.InlineKeyboardButton(text='Guilds', callback_data='guilds')
        reply_markup = telegram.InlineKeyboardMarkup([[buttonLvl, buttonBounty, buttonGuilds]])
        await query.edit_message_text(parse_mode='HTML', text="Which top would you like to consult?",
                                      reply_markup=reply_markup)

    conn.commit()
    conn.close()


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """allows users to restart from zero"""
    if not await user_registered(update):
        await warning_unregistered_user(update, context)
        return
    if await check_chat(update):
        await warning_chat(update)
        return
    if await user_banned(update):
        return

    testo = "Do you want to reset your account?"
    button_si = telegram.InlineKeyboardButton(text='Yes', callback_data='yes')
    button_no = telegram.InlineKeyboardButton(text='No', callback_data='no')
    await update.message.reply_text(text=testo, reply_markup=telegram.InlineKeyboardMarkup([[button_si, button_no]]))


async def reset_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage buttons of reset function"""
    conn = sqlite3.connect('dungeon.db')
    c = conn.cursor()
    query = update.callback_query
    cbd = update.callback_query.data
    if cbd == 'yes':
        user_id = update.callback_query.from_user.id
        c.execute("DELETE FROM Profile WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM User WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM Messages WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM Inventory WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM Guild WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM Equipment WHERE user_id = ?", (user_id,))
        try:
            c.execute("DELETE FROM '{}'".format(user_id, ))
        except:
            pass

        conn.commit()
        conn.close()
        await query.edit_message_text(parse_mode='HTML', text='<b>You lost your account</b>')
    if cbd == 'no':
        await query.edit_message_text(parse_mode='HTML', text='<b>Your account is safe</b>')