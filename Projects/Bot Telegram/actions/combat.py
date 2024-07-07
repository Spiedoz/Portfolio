import sqlite3
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from users.stats import upgrade
from utils.helpers import user_banned, user_registered, check_chat, warning_unregistered_user, warning_chat

import logging

# Set logging level for apscheduler to WARNING to reduce console output
logging.getLogger('apscheduler').setLevel(logging.WARNING)


def remove_existing_monster_flee_jobs(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """Remove monster flee jobs for the given user. Returns whether any job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(f'monster_flee_{user_id}')
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def create_hp_bar(current_hp, max_hp, length=10):
    """Create a hp bar, useful for improving the visual of the battle message."""
    filled_length = int(length * current_hp / max_hp)
    bar = '█' * filled_length + '░' * (length - filled_length)
    return bar


async def battle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check if the user can engage the battle with the monster"""
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

    user_id = update.effective_message.from_user.id

    status = c.execute("SELECT status FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]

    if status == 'in_battle':
        try:
            await continue_battle(update, context)
        except:
            await update.message.reply_text("Use the appropriate buttons to battle")
    else:
        await start_new_battle(update, context)

    conn.close()


async def start_new_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initializes the battle between a monster and the user"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    user_id = update.effective_message.from_user.id

    try:
        monster_id = c.execute("SELECT monster_id FROM Duel WHERE user_id = ?", (user_id,)).fetchone()[0]
    except:
        await update.message.reply_text("There is no monster to battle against!")
        return



    nickname = c.execute("SELECT nickname FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    playerHP = c.execute("SELECT hp FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]
    monsterName = c.execute("SELECT name FROM '{}' WHERE monster_id = ?".format(user_id,), (monster_id,)).fetchone()[0]
    monsterHP = c.execute("SELECT hp FROM '{}' WHERE monster_id = ?".format(user_id,), (monster_id,)).fetchone()[0]

    c.execute("UPDATE Profile SET status = 'in_battle' WHERE user_id = ?", (user_id,))

    playerHPMax = c.execute("SELECT hp_max FROM Profile WHERE user_id = ?",
                                 (user_id,)).fetchone()[0]
    monsterHPMax = c.execute("SELECT hp_max FROM '{}' WHERE monster_id = ?".format(user_id),
                              (monster_id,)).fetchone()[0]

    playerHPBar = create_hp_bar(playerHP, playerHPMax)
    monsterHPBar = create_hp_bar(monsterHP, monsterHPMax)

    battle_text = (
        f"<b>{nickname}</b> encounters <b>{monsterName}</b>!\n\n"
        f"<b>{nickname}'s HP:</b> {playerHP:}/{playerHPMax}\n"
        f"{playerHPBar}\n\n"
        f"<b>{monsterName}'s HP:</b> {monsterHP}/{monsterHPMax:}\n"
        f"{monsterHPBar}"
    )

    keyboard = [[InlineKeyboardButton("Continue", callback_data='continue_battle')],
                [InlineKeyboardButton("Flee", callback_data='flee_battle')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    battle_message = await update.message.reply_text(battle_text, reply_markup=reply_markup,
                                                     parse_mode='HTML')
    c.execute("UPDATE Duel SET message_id = ? WHERE user_id = ?", (battle_message.message_id, user_id,))

    conn.commit()
    conn.close()

    remove_existing_monster_flee_jobs(context, user_id)
    context.job_queue.run_once(
        monster_flee,
        90,
        chat_id=update.effective_chat.id,
        name=f'monster_flee_{user_id}',
        user_id=user_id,
        data={'user_id': user_id, 'message_id': battle_message.message_id}
    )


async def continue_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Once the user choose to continue the battle, one turn goes on
    and calculate the actual damage done to each other
    """
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    user_id = query.from_user.id

    nickname = c.execute("SELECT nickname FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    playerClass = c.execute("SELECT class FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]
    playerHP = c.execute("SELECT hp FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]
    playerAtk = c.execute("SELECT atk FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]
    playerAtkBonus = c.execute("SELECT atk_bonus FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]
    playerDef = c.execute("SELECT def FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]
    playerDefBonus = c.execute("SELECT def_bonus FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]
    playerCrit = c.execute("SELECT crit FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]
    playerVel = c.execute("SELECT vel FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]

    monster_id = c.execute("SELECT monster_id FROM Duel WHERE user_id = ?", (user_id,)).fetchone()[0]
    monsterName = c.execute("SELECT name FROM '{}' WHERE monster_id = ?".format(user_id), (monster_id,)).fetchone()[0]
    monsterHP = c.execute("SELECT hp FROM '{}' WHERE monster_id = ?".format(user_id), (monster_id,)).fetchone()[0]
    monsterAtk = c.execute("SELECT atk FROM '{}' WHERE monster_id = ?".format(user_id), (monster_id,)).fetchone()[0]
    monsterDef = c.execute("SELECT def FROM '{}' WHERE monster_id = ?".format(user_id), (monster_id,)).fetchone()[0]
    monsterCrit = c.execute("SELECT crit FROM '{}' WHERE monster_id = ?".format(user_id), (monster_id,)).fetchone()[0]
    monsterVel = c.execute("SELECT vel FROM '{}' WHERE monster_id = ?".format(user_id), (monster_id,)).fetchone()[0]

    playerHPMax = c.execute("SELECT hp_max FROM Profile WHERE user_id = ?",
                                 (user_id,)).fetchone()[0]
    monsterHPMax = c.execute("SELECT hp_max FROM '{}' WHERE monster_id = ?".format(user_id),
                              (monster_id,)).fetchone()[0]

    battle_text = ""
    turn = c.execute("SELECT turn FROM Duel WHERE user_id = ?", (user_id,)).fetchone()[0]

    # checking who goes first by comparing the speeds
    if playerVel >= monsterVel:
        damage_to_monster, is_crit_player = damageCalculation(playerAtk, playerAtkBonus, monsterDef, 0, playerCrit)
        monsterHP -= damage_to_monster
        battle_text += f"<b>{nickname}</b> deals {damage_to_monster:} damage.\n"
        if is_crit_player:
            battle_text += "<b>(Critical Hit!)\n\n</b>"

        if monsterHP > 0:
            damage_to_player, is_crit_monster = damageCalculation(monsterAtk, 0, playerDef, playerDefBonus, monsterCrit)
            if turn == 1 and playerClass in ['Assassin', 'Shadow']:
                battle_text += f"<b>{monsterName}</b> tries to attack, but <b>{nickname}</b> dodges!"
            else:
                playerHP -= damage_to_player
                battle_text += f"<b>{monsterName}</b> deals {damage_to_player} damage.\n"
                if is_crit_monster:
                    battle_text += "<b>(Critical Hit!)</b>"

    else:
        damage_to_player, is_crit_monster = damageCalculation(monsterAtk, 0, playerDef, playerDefBonus, monsterCrit)
        if turn == 1 and playerClass in ['Assassin', 'Shadow']:
            battle_text += f"<b>{monsterName}</b> tries to attack, but <b>{nickname}</b> dodges!\n"
        else:
            playerHP -= damage_to_player
            battle_text += f"<b>{monsterName}</b> deals {damage_to_player} damage.\n"
            if is_crit_monster:
                battle_text += "<b>(Critical Hit!)</b>\n\n"

        if playerHP > 0:
            damage_to_monster, is_crit_player = damageCalculation(playerAtk, playerAtkBonus, monsterDef, 0, playerCrit)
            monsterHP -= damage_to_monster
            battle_text += f"<b>{nickname}</b> deals {damage_to_monster} damage.\n"
            if is_crit_player:
                battle_text += "<b>(Critical Hit!)</b>"

    # updating the hp of both
    c.execute("UPDATE Profile SET hp = ? WHERE user_id = ?", (playerHP, user_id,))
    c.execute("UPDATE '{}' SET hp = ? WHERE monster_id = ?".format(user_id), (monsterHP, monster_id,))

    c.execute("UPDATE Duel SET turn = (SELECT turn FROM Duel WHERE user_id = ?)+1 WHERE user_id = ?",
              (user_id, user_id,))

    playerHPBar = create_hp_bar(playerHP, playerHPMax)
    monsterHPBar = create_hp_bar(monsterHP, monsterHPMax)

    battle_text = (
        f"<b>Turn:</b> {turn}\n\n"
        f"<b>{nickname}'s HP:</b> {playerHP}/{playerHPMax}\n"
        f"{playerHPBar}\n\n"
        f"<b>{monsterName}'s HP:</b> {monsterHP}/{monsterHPMax}\n"
        f"{monsterHPBar}\n\n"
        f"{battle_text}"
    )

    keyboard = [[InlineKeyboardButton("Continue", callback_data='continue_battle')],
                [InlineKeyboardButton("Flee", callback_data='flee_battle')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    remove_existing_monster_flee_jobs(context, user_id)
    context.job_queue.run_once(
        monster_flee,
        90,
        chat_id=update.effective_chat.id,
        name=f'monster_flee_{user_id}',
        user_id=user_id,
        data={'user_id': user_id, 'message_id': query.message.message_id}
    )

    await query.edit_message_text(text=battle_text, reply_markup=reply_markup, parse_mode='HTML')

    conn.commit()

    # checking death
    if playerHP <= 0:
        await death(update, context, monster_id)
        c.execute("UPDATE Profile SET status = 'exploring' WHERE user_id = ?", (user_id,))
    elif monsterHP <= 0:
        await victory(update, context, monster_id)
        await upgrade(update, context)
        c.execute("UPDATE Profile SET status = 'exploring' WHERE user_id = ?", (user_id,))
    else:
        remove_existing_monster_flee_jobs(context, user_id)
        context.job_queue.run_once(
            monster_flee,
            90,
            chat_id=update.effective_chat.id,
            name=f'monster_flee_{user_id}',
            user_id=user_id,
            data={'user_id': user_id, 'message_id': query.message.message_id}
        )

    conn.commit()
    conn.close()


async def flee_battle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Allows user to escape from the battle"""
    query = update.callback_query
    await query.answer()
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    user_id = query.from_user.id

    c.execute("DELETE FROM '{}' WHERE monster_id = (SELECT monster_id FROM Duel WHERE user_id = ?)".format(user_id),
              (user_id,))
    c.execute("DELETE FROM Duel WHERE user_id = ?", (user_id,))
    c.execute("UPDATE Profile SET status = 'exploring' WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()

    remove_existing_monster_flee_jobs(context, user_id)
    await query.message.edit_text("You fled from the battle!")


async def monster_flee(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Once the timer is out the monster will escape from the battle"""
    job = context.job
    user_id = job.data['user_id']
    message_id = job.data['message_id']
    chat_id = job.chat_id

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    try:
        status = c.execute("SELECT status FROM Profile WHERE user_id = ?", (user_id,)).fetchone()
        if not status or status[0] != 'in_battle':
            return

        c.execute("UPDATE Profile SET status = 'monster_fleeing' WHERE user_id = ?", (user_id,))
        conn.commit()

        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="The monster has fled after waiting for too long!"
            )
        except BadRequest:
            await context.bot.send_message(chat_id=chat_id, text="The monster has fled after waiting for too long!")

        c.execute("DELETE FROM '{}' WHERE monster_id = (SELECT monster_id FROM Duel WHERE user_id = ?)".format(user_id),
                  (user_id,))
        c.execute("DELETE FROM Duel WHERE user_id = ?", (user_id,))
        c.execute("UPDATE Profile SET status = 'exploring' WHERE user_id = ?", (user_id,))

        conn.commit()
    finally:
        conn.close()

    remove_existing_monster_flee_jobs(context, user_id)


def damageCalculation(atk, atk_bonus, defe, def_bonus, crit):
    """Calculation of both user and monster damage"""
    base_damage = atk + random.randint(0, atk_bonus)
    defense = defe + random.randint(0, def_bonus)

    min_damage = max(1, int(atk * 0.1))

    damage = max(min_damage, base_damage - defense)

    is_crit = random.random() < (crit / 100)
    if is_crit:
        crit_multiplier = random.uniform(1.5, 2.0)
        crit_damage = max(damage + 1, int(damage * crit_multiplier))

        damage = crit_damage

    return damage, is_crit


async def death(update: Update, context: ContextTypes.DEFAULT_TYPE, mostro_id) -> None:
    """manage the death of the user"""
    conn = sqlite3.connect("dungeon.db")
    u = conn.cursor()
    user_id = update.callback_query.from_user.id
    query = update.callback_query

    monsterName = u.execute("SELECT name FROM '{}' WHERE monster_id = ?".format(user_id,), (mostro_id,)).fetchone()[0]
    exp_user = u.execute("SELECT exp FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    loss = int(int(exp_user * 50) / 100)
    playerHPMax = u.execute("SELECT hp_max FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]

    u.execute("UPDATE Profile SET status = 'exploring' WHERE user_id = ?", (user_id,))
    u.execute("DELETE FROM '{}'".format(user_id,))
    u.execute("DELETE FROM Duel WHERE user_id = ?", (user_id,))
    u.execute("UPDATE User SET exp = (SELECT exp FROM User WHERE user_id = ?) - ? WHERE user_id = ?",
              (user_id, loss, user_id))
    if exp_user <= 0:
        u.execute("UPDATE User SET exp = ? WHERE user_id = ?", (0, user_id,))
    u.execute("UPDATE Profile SET hp = ? WHERE user_id = ?", (playerHPMax, user_id,))
    text = f"You were killed by the <b>{monsterName}</b> and you lost many exp!"
    await query.edit_message_text(text, parse_mode='HTML')

    remove_existing_monster_flee_jobs(context, user_id)

    conn.commit()
    conn.close()


async def victory(update: Update, context: ContextTypes.DEFAULT_TYPE, mostro_id) -> None:
    """manage the victory of user"""
    conn = sqlite3.connect("dungeon.db")
    u = conn.cursor()
    user_id = update.callback_query.from_user.id
    query = update.callback_query

    monsterLvl = u.execute("SELECT lvl FROM '{}' WHERE monster_id = ?".format(user_id), (mostro_id,)).fetchone()[0]
    monsterName = u.execute("SELECT name FROM '{}' WHERE monster_id = ?".format(user_id), (mostro_id,)).fetchone()[0]
    monsterRarity = u.execute("SELECT rarity FROM '{}' WHERE monster_id = ?".format(user_id), (mostro_id,)).fetchone()[0]
    exp = random.randint(monsterLvl, monsterLvl*2)
    reward = int(exp/2+1)
    bounty = 50 * monsterLvl if monsterRarity == 'SR' else 0

    u.execute("UPDATE Profile SET status = 'exploring' WHERE user_id = ?", (user_id,))
    u.execute("DELETE FROM '{}'".format(user_id,))
    u.execute("UPDATE User SET exp = (SELECT exp FROM User WHERE user_id = ?) + ? WHERE user_id = ?",
              (user_id, exp, user_id,))
    u.execute("UPDATE User SET gold = (SELECT gold FROM User WHERE user_id = ?) + ? WHERE user_id = ?",
              (user_id, reward, user_id,))
    u.execute("UPDATE User SET bounty = (SELECT bounty FROM User WHERE user_id = ?) + ? WHERE user_id = ?",
              (user_id, bounty, user_id,))
    text = f"You killed {monsterName} (Lvl. {monsterLvl}) and gain <b>{reward} gold</b>!\n<i>+{exp} exp</i>\n\n"
    if bounty != 0:
        text += f"\nBy defeating the dungeon boss you have earned reputation. Your bounty went up by: <b>{bounty}</b>|"
    await query.edit_message_text(parse_mode='HTML', text=text)
    u.execute("DELETE FROM Duel WHERE user_id = ?", (user_id,))

    remove_existing_monster_flee_jobs(context, user_id)

    conn.commit()
    conn.close()