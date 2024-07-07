import telegram
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from utils.helpers import user_registered, user_banned, check_chat, warning_unregistered_user, warning_chat


async def found(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """creates a new guild"""
    conn = sqlite3.connect('dungeon.db')
    c = conn.cursor()

    if not await user_registered(update):
        await warning_unregistered_user(update, context)
        return

    if await check_chat(update):
        await warning_chat(update)
        return

    if await user_banned(update):
        return

    try:
        guildName = update.message.text.split(' ', 1)[1]
    except IndexError:
        return

    user_id = update.effective_message.from_user.id

    if c.execute("SELECT COUNT(*) FROM Guild WHERE user_id = ?", (user_id,)).fetchone()[0] > 0:
        await update.message.reply_text(parse_mode='HTML', text="You can't found a new guild if you are already part of one!")
        return

    if c.execute("SELECT * FROM Guild WHERE name=?", (guildName,)).fetchall():
        await update.message.reply_text(parse_mode='HTML', text="It seems that this name has already been taken by another guild, choose another one!")
        return

    if len(guildName) > 20:
        await update.message.reply_text(parse_mode='HTML', text="Maximum number of characters reached! Choose a shorter name!")
        return

    price = 500
    user_bounty = c.execute("SELECT bounty FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    user_gold = c.execute("SELECT gold FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]

    if user_gold < price:
        await update.message.reply_text(parse_mode='HTML', text="You don't have enough gold to found a guild!\n<i>(You need 500 gold!)</i>")
        return

    c.execute("UPDATE User SET gold = gold - ? WHERE user_id = ?", (price, user_id))
    c.execute("INSERT INTO Guild (name, user_id, role, bounty) VALUES (?, ?, ?, ?)", (guildName, user_id, "Leader", user_bounty))
    conn.commit()
    conn.close()

    await update.message.reply_text(parse_mode='HTML', text=f"You founded the new guild: <b>{guildName}</b>!\n"
                                                            f"Start recruiting new members to increase your guild's prestige!")


async def guild(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """gives user information of the guild if joined/founded one"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    if not await user_registered(update):
        await warning_unregistered_user(update, context)
        return

    if await user_banned(update):
        return

    user_id = update.effective_message.from_user.id
    user_guilds = c.execute("SELECT * FROM Guild WHERE user_id = ?", (user_id,)).fetchall()

    if not user_guilds:
        await update.message.reply_text(parse_mode='HTML', text="You are not part of any Guild!")
        return

    guild = c.execute("SELECT name FROM Guild WHERE user_id = ?", (user_id,)).fetchone()[0]
    guild_bounties = c.execute("SELECT bounty FROM Guild WHERE name = ?", (guild,)).fetchall()
    total_bounty = sum(bounty[0] for bounty in guild_bounties)

    if c.execute("SELECT COUNT(*) FROM Guilds WHERE name = ?", (guild,)).fetchone()[0] == 0:
        c.execute("INSERT INTO Guilds (name, bounty) VALUES (?, ?)", (guild, total_bounty))
    else:
        c.execute("UPDATE Guilds SET bounty = ? WHERE name = ?", (total_bounty, guild))

    members_count = c.execute("SELECT COUNT(*) FROM Guild WHERE name = ?", (guild,)).fetchone()[0]
    recruits_count = c.execute("SELECT COUNT(*) FROM Guild WHERE name = ? AND role = ?", (guild, "Recruit")).fetchone()[0]
    elders_count = c.execute("SELECT COUNT(*) FROM Guild WHERE name = ? AND role = ?", (guild, "Elder")).fetchone()[0]
    co_leaders_count = c.execute("SELECT COUNT(*) FROM Guild WHERE name = ? AND role = ?", (guild, "Co-leader")).fetchone()[0]
    leader_id = c.execute("SELECT user_id FROM Guild WHERE name = ? AND role = ?", (guild, "Leader")).fetchone()[0]
    leader_nickname = c.execute("SELECT nickname FROM User WHERE user_id = ?", (leader_id,)).fetchone()[0]
    guild_bounty = c.execute("SELECT bounty FROM Guilds WHERE name = ?", (guild,)).fetchone()[0]

    text = (f"{guild}:\n\n<b>Leader:</b> <i>{leader_nickname}</i>\n"
            f"<b>Bounty:</b> <i>{guild_bounty}</i>\n"
            f"<b>Members:</b> <i>{members_count}</i>\n"
            f"<b>Recruits</b>: <i>{recruits_count}</i>\n"
            f"<b>Elders:</b> <i>{elders_count}</i>\n"
            f"<b>Co-leaders:</b> <i>{co_leaders_count}</i>")

    await update.message.reply_text(parse_mode='HTML', text=text)
    conn.commit()
    conn.close()

async def setGuild(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """changes name of the guild if founded one"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    if not await user_registered(update):
        await warning_unregistered_user(update, context)
        return

    if await check_chat(update):
        await warning_chat(update)
        return

    if await user_banned(update):
        return

    try:
        new_guild_name = update.message.text.split(' ', 1)[1]
    except IndexError:
        return

    user_id = update.effective_message.from_user.id

    user_guilds = c.execute("SELECT * FROM Guild WHERE user_id = ?", (user_id,)).fetchall()

    if not user_guilds:
        await update.message.reply_text(parse_mode='HTML', text="You can't use this command if you don't belong to any Guild!")
        return

    user_role = c.execute("SELECT role FROM Guild WHERE user_id = ?", (user_id,)).fetchone()[0]

    if user_role != 'Leader':
        await update.message.reply_text(parse_mode='HTML', text="Only the <b>Leader</b> can change the name of the guild!")
        return

    if c.execute("SELECT * FROM Guild WHERE name = ?", (new_guild_name,)).fetchall():
        await update.message.reply_text(parse_mode='HTML', text="It seems that this name has already been taken by another guild, choose another one!")
        return

    if len(new_guild_name) > 20:
        await update.message.reply_text(parse_mode='HTML', text="Maximum number of characters reached! Choose a shorter name!")
        return

    current_guild_name = c.execute("SELECT name FROM Guild WHERE user_id = ?", (user_id,)).fetchone()[0]
    guild_members = c.execute("SELECT user_id FROM Guild WHERE name = ?", (current_guild_name,)).fetchall()

    user_gold = c.execute("SELECT gold FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]

    if user_gold < 500:
        await update.message.reply_text(parse_mode='HTML', text="You don't have enough gold to change your guild's name!\n<i>(You need 500 gold)</i>")
        return

    c.execute("UPDATE Guilds SET name = ? WHERE name = ?", (new_guild_name, current_guild_name))
    c.execute("UPDATE User SET gold = gold - 500 WHERE user_id = ?", (user_id,))
    for member in guild_members:
        c.execute("UPDATE Guild SET name = ? WHERE user_id = ?", (new_guild_name, member[0]))

    conn.commit()
    conn.close()

    await update.message.reply_text(parse_mode='HTML', text=f"Your Guild's name is now: <b>{new_guild_name}</b>!")

async def members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """shows members of the guild"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    if not await user_registered(update):
        await warning_unregistered_user(update, context)
        return

    if await user_banned(update):
        return

    user_id = update.effective_message.from_user.id

    user_guilds = c.execute("SELECT * FROM Guild WHERE user_id = ?", (user_id,)).fetchall()

    if not user_guilds:
        await update.message.reply_text(parse_mode='HTML', text="You can't use this command if you don't belong to any Guild!")
        return

    user_role = c.execute("SELECT role FROM Guild WHERE user_id = ?", (user_id,)).fetchone()[0]

    if user_role not in ['Leader', 'Co-Leader']:
        await update.message.reply_text(parse_mode='HTML',
                                        text="Only the <b>Co-Leaders</b> and <b>Leader</b> can check the members")
        return

    guild = c.execute("SELECT name FROM Guild WHERE user_id = ?", (user_id,)).fetchone()[0]
    guild_members = c.execute("SELECT * FROM Guild WHERE name = ? ORDER BY role LIMIT 15", (guild,)).fetchall()

    text = f"<b>Guild:</b> <i>{guild}</i>\n\n<b>Members:</b>\n"
    for i, member in enumerate(guild_members):
        nickname, lvl = c.execute("SELECT nickname, lvl FROM User WHERE user_id = ?", (member[1],)).fetchone()
        text += f"- <b>{nickname}</b> (Lvl. {lvl}) [{member[2]}]\n"

    await update.message.reply_text(parse_mode='HTML', text=text)
    conn.close()


async def members_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manages pages of the member function"""
    conn = sqlite3.connect('dungeon.db')
    try:
        c = conn.cursor()
        query = update.callback_query
        if query is None or query.data is None:
            return

        page = int(query.data.split(':', 1)[1])
        offset = (page - 1) * 15
        guild = c.execute("SELECT name FROM Guild WHERE user_id = ?", (query.from_user.id,)).fetchone()[0]
        members = c.execute("SELECT * FROM Guild WHERE name = ? ORDER BY role LIMIT 15 OFFSET ?",
                            (guild, offset)).fetchall()
        text = f"Members list <b>{guild}:</b> <i>(Pag. {page})</i>\n\n"
        if members:
            for member in members:
                nickname, lvl = c.execute("SELECT nickname, lvl FROM User WHERE user_id = ?", (member[1],)).fetchone()
                text += f"- <b>{nickname}</b> (Lvl. {lvl}) [{member[2]}]\n"
            kb = []
            if page > 1:
                kb.append(InlineKeyboardButton(text=f'< Page {page - 1}', callback_data=f'members_page:{page - 1}'))
            kb.append(InlineKeyboardButton(text=f'Page {page + 1} >', callback_data=f'members_page:{page + 1}'))
            await query.edit_message_text(parse_mode='HTML', text=text, reply_markup=InlineKeyboardMarkup([kb]))
        else:
            await context.bot.answer_callback_query(callback_query_id=query.id, text='Empty List')
    finally:
        conn.commit()
        conn.close()


async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """invitation to users to own guild"""
    conn = sqlite3.connect("dungeon.db")
    try:
        c = conn.cursor()
        if not await user_registered(update):
            await warning_unregistered_user(update, context)
        else:
            if not await user_banned(update):
                try:
                    target_user_id = update.message.reply_to_message.from_user.id
                except AttributeError:
                    return

                guild = c.execute("SELECT name FROM Guild WHERE user_id = ?", (update.effective_message.from_user.id,)).fetchone()[0]
                c.execute("INSERT INTO Invite(guild, id_invited) VALUES (?, ?)", (guild, target_user_id))
                targetNickname = c.execute("SELECT nickname FROM User WHERE user_id = ?", (target_user_id,)).fetchone()[0]
                text = f"You sent an invite to <b>{targetNickname}</b>. Wait for him/her to accept or decline the invitation!"
                await update.message.reply_text(parse_mode='HTML', text=text)

                chat_id = c.execute("SELECT chat_id FROM User WHERE user_id = ?", (target_user_id,)).fetchone()[0]
                buttonAccept = telegram.InlineKeyboardButton(text='Accept', callback_data='accept')
                buttonDecline = telegram.InlineKeyboardButton(text='Decline', callback_data='decline')
                reply_markup = telegram.InlineKeyboardMarkup([[buttonAccept, buttonDecline]])
                textP = f"You have been invited to join the guild: <b>{guild}</b>. Do you accept or decline the invite?"
                await context.bot.send_message(chat_id=chat_id, parse_mode='HTML', text=textP, reply_markup=reply_markup)
    finally:
        conn.commit()
        conn.close()


async def invite_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage decision of the invited users"""
    conn = sqlite3.connect("dungeon.db")
    try:
        c = conn.cursor()
        query = update.callback_query
        cbd = query.data
        user_id = query.from_user.id
        if cbd == 'accept':
            gilda = c.execute("SELECT Guild FROM Invite WHERE id_invited = ?", (user_id,)).fetchone()[0]
            bounty = c.execute("SELECT bounty FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
            if c.execute("SELECT COUNT(*) FROM Guild WHERE user_id = ?", (user_id,)).fetchone()[0] == 0:
                c.execute("INSERT INTO Guild(name, user_id, role, bounty) VALUES (?, ?, ?, ?)",
                          (gilda, user_id, "Recruit", bounty))
                text = f"You accepted the invitation and you are now part of the guild <b>{gilda}</b>!"
                c.execute("DELETE FROM Invite WHERE id_invited = ?", (user_id,))
                await query.edit_message_text(parse_mode='HTML', text=text)
            else:
                await context.bot.answer_callback_query(callback_query_id=query.id, text="You're already in a guild!")
        elif cbd == 'decline':
            text = "You declined the invite."
            c.execute("DELETE FROM Invite WHERE id_invited = ?", (user_id,))
            await query.edit_message_text(parse_mode='HTML', text=text)
    finally:
        conn.commit()
        conn.close()



async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """promote role of targeted user"""
    conn = sqlite3.connect("dungeon.db")
    try:
        c = conn.cursor()
        if not await user_registered(update):
            await warning_unregistered_user(update, context)
        else:
            if not await user_banned(update):
                try:
                    target_user_id = update.message.reply_to_message.from_user.id
                except AttributeError:
                    return

                user_id = update.effective_message.from_user.id
                playerRole = c.execute("SELECT role FROM Guild WHERE user_id = ?", (user_id,)).fetchone()[0]
                targetRole = c.execute("SELECT role FROM Guild WHERE user_id = ?", (target_user_id,)).fetchone()[0]
                playerGuild = c.execute("SELECT name FROM Guild WHERE user_id = ?", (user_id,)).fetchone()[0]
                targetGuild = c.execute("SELECT name FROM Guild WHERE user_id = ?", (target_user_id,)).fetchone()[0]
                targetNickname = c.execute("SELECT nickname FROM User WHERE user_id = ?", (target_user_id,)).fetchone()[0]

                if playerRole in ['Leader', 'Co-Leader']:
                    if user_id == target_user_id:
                        return
                    else:
                        if playerGuild == targetGuild:
                            if targetRole == 'Recruit':
                                c.execute("UPDATE Guild SET role = ? WHERE user_id = ?", ("Elder", target_user_id))
                                text = f"{targetNickname} is now an <b>Elder</b>!"
                            elif targetRole == 'Elder':
                                c.execute("UPDATE Guild SET role = ? WHERE user_id = ?", ("Co-Leader", target_user_id))
                                text = f"{targetNickname} is now a <b>Co-leader</b>!"
                            elif targetRole == 'Co-leader':
                                text = "This player can't be promoted!"
                            elif targetRole == 'Leader':
                                return
                            await update.message.reply_text(parse_mode='HTML', text=text)
                        else:
                            return
                else:
                    text = "You can't use this command, only <b>Co-leaders</b> and <b>Leader</b> can!"
                    await update.message.reply_text(parse_mode='HTML', text=text)
    finally:
        conn.commit()
        conn.close()



async def degrade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """degrade role of the targeted user"""
    conn = sqlite3.connect("dungeon.db")
    try:
        c = conn.cursor()
        if not await user_registered(update):
            await warning_unregistered_user(update, context)
        else:
            if not await user_banned(update):
                try:
                    target_user_id = update.message.reply_to_message.from_user.id
                except AttributeError:
                    return

                user_id = update.effective_message.from_user.id
                playerRole = c.execute("SELECT role FROM Guild WHERE user_id = ?", (user_id,)).fetchone()[0]
                targetRole = c.execute("SELECT role FROM Guild WHERE user_id = ?", (target_user_id,)).fetchone()[0]
                playerGuild = c.execute("SELECT name FROM Guild WHERE user_id = ?", (user_id,)).fetchone()[0]
                targetGuild = c.execute("SELECT name FROM Guild WHERE user_id = ?", (target_user_id,)).fetchone()[0]
                targetNickname = c.execute("SELECT nickname FROM User WHERE user_id = ?", (target_user_id,)).fetchone()[0]

                if playerRole in ['Leader', 'Co-Leader']:
                    if user_id == target_user_id:
                        return
                    else:
                        if playerGuild == targetGuild:
                            if targetRole == 'Recruit':
                                return
                            elif targetRole == 'Elder':
                                c.execute("UPDATE Guild SET role = ? WHERE user_id = ?", ("Recruit", target_user_id))
                                text = f"{targetNickname} is now a <b>Recruit</b>"
                            elif targetRole == 'Co-leader':
                                if playerRole == targetRole:
                                    return
                                else:
                                    c.execute("UPDATE Guild SET role = ? WHERE user_id = ?", ("Elder", target_user_id))
                                    text = f"{targetNickname} is now an <b>Elder</b>"
                            elif targetRole == 'Leader':
                                return
                            await update.message.reply_text(parse_mode='HTML', text=text)
                        else:
                            return
                else:
                    text = "You can't use this command, only <b>Co-leaders</b> and <b>Leader</b> can!"
                    await update.message.reply_text(parse_mode='HTML', text=text)
    finally:
        conn.commit()
        conn.close()


async def kickout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """remove member from the guild"""
    conn = sqlite3.connect("dungeon.db")
    try:
        c = conn.cursor()
        if not await user_registered(update):
            await warning_unregistered_user(update, context)
        else:
            if not await user_banned(update):
                try:
                    nickname = update.message.text.split(' ', 1)[1]
                except IndexError:
                    return

                target_user_id = c.execute("SELECT user_id FROM User WHERE nickname = ?", (nickname,)).fetchone()
                if target_user_id is None:
                    return

                target_user_id = target_user_id[0]
                user_id = update.effective_message.from_user.id
                playerRole = c.execute("SELECT role FROM Guild WHERE user_id = ?", (user_id,)).fetchone()[0]
                playerGuild = c.execute("SELECT name FROM Guild WHERE user_id = ?", (user_id,)).fetchone()[0]
                targetGuild = c.execute("SELECT name FROM Guild WHERE user_id = ?", (target_user_id,)).fetchone()[0]
                targetNickname = c.execute("SELECT nickname FROM User WHERE user_id = ?", (target_user_id,)).fetchone()[
                    0]

                if playerRole in ['Leader', 'Co-Leader']:
                    if user_id == target_user_id:
                        return
                    else:
                        if playerGuild == targetGuild:
                            c.execute("DELETE FROM Guild WHERE user_id = ?", (target_user_id,))
                            text = f"<b>{targetNickname}</b> is no longer part of the guild."
                            await update.message.reply_text(parse_mode='HTML', text=text)
                        else:
                            return
                else:
                    text = "You can't use this command, only <b>Co-leaders</b> and <b>Leader</b> can!"
                    await update.message.reply_text(parse_mode='HTML', text=text)
    finally:
        conn.commit()
        conn.close()


async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """allows users to abandon the guild"""
    conn = sqlite3.connect("dungeon.db")
    try:
        c = conn.cursor()
        if not await user_registered(update):
            await warning_unregistered_user(update, context)
        else:
            if await check_chat(update):
                await warning_chat(update)
            else:
                if not await user_banned(update):
                    if c.execute("SELECT * FROM Guild WHERE user_id = ?", (update.effective_message.from_user.id,)).fetchall():
                        guild = c.execute("SELECT name FROM Guild WHERE user_id = ?", (update.effective_message.from_user.id,)).fetchone()[0]
                        text = f"You left the guild: <b>{guild}</b>."
                        await update.message.reply_text(parse_mode='HTML', text=text)
                        c.execute("DELETE FROM Guild WHERE user_id = ?", (update.effective_message.from_user.id,))
                        g = c.execute("SELECT COUNT(*) FROM Guild WHERE name = ?", (guild,)).fetchone()[0]
                        if g == 0:
                            c.execute("DELETE FROM Guilds WHERE name = ?", (guild,))
                    else:
                        text = "You can't use this command if you don't belong to any Guild!"
                        await update.message.reply_text(parse_mode='HTML', text=text)
    finally:
        conn.commit()
        conn.close()
