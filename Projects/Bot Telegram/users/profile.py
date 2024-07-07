import telegram
import sqlite3
from telegram.ext import ContextTypes
from telegram import Update
from asset.asset import get_area_info, getClass_info, fetch_weapons
from utils.helpers import (user_is_trading, user_registered, user_banned, check_chat,
                           warning_trading_user, warning_unregistered_user, warning_chat)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """shows stats of user"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    if not await user_registered(update):
        await warning_unregistered_user(update, context)
    else:
        if not await user_banned(update):
            nickname = c.execute("SELECT nickname FROM User WHERE user_id = ?",
                                 (update.effective_message.from_user.id,)).fetchone()[0]
            playerLvl = c.execute("SELECT lvl FROM User WHERE user_id = ?",
                                (update.effective_message.from_user.id,)).fetchone()[0]
            expNeeded = playerLvl * 50
            exp = c.execute("SELECT exp FROM User WHERE user_id = ?",
                            (update.effective_message.from_user.id,)).fetchone()[0]
            gold = c.execute("SELECT gold FROM User WHERE user_id = ?",
                               (update.effective_message.from_user.id,)).fetchone()[0]
            bounty = c.execute("SELECT bounty FROM User WHERE user_id = ?",
                               (update.effective_message.from_user.id,)).fetchone()[0]
            playerClass = c.execute("SELECT class FROM Profile WHERE user_id = ?",
                               (update.effective_message.from_user.id,)).fetchone()[0]
            playerHP = c.execute("SELECT hp FROM Profile WHERE user_id = ?",
                             (update.effective_message.from_user.id,)).fetchone()[0]
            playerHPMax = c.execute("SELECT hp_max FROM Profile WHERE user_id = ?",
                                 (update.effective_message.from_user.id,)).fetchone()[0]
            playerAtk = c.execute("SELECT atk FROM Profile WHERE user_id = ?",
                                (update.effective_message.from_user.id,)).fetchone()[0]
            playerAtkBonus = c.execute("SELECT atk_bonus FROM Profile WHERE user_id = ?",
                                      (update.effective_message.from_user.id,)).fetchone()[0]
            playerDef = c.execute("SELECT def FROM Profile WHERE user_id = ?",
                               (update.effective_message.from_user.id,)).fetchone()[0]
            playerDefBonus = c.execute("SELECT def_bonus FROM Profile WHERE user_id = ?",
                                     (update.effective_message.from_user.id,)).fetchone()[0]
            playerVel = c.execute("SELECT vel FROM Profile WHERE user_id = ?",
                                     (update.effective_message.from_user.id,)).fetchone()[0]
            playerVelBonus = c.execute("SELECT vel_bonus FROM Profile WHERE user_id = ?",
                                     (update.effective_message.from_user.id,)).fetchone()[0]
            playerCrit = c.execute("SELECT crit FROM Profile WHERE user_id = ?",
                                     (update.effective_message.from_user.id,)).fetchone()[0]
            stats_points = c.execute("SELECT stats_points FROM Profile WHERE user_id = ?",
                                    (update.effective_message.from_user.id,)).fetchone()[0]

            g = c.execute("SELECT * FROM Guild WHERE user_id = ?",
                          (str(update.effective_message.from_user.id),)).fetchall()
            if len(g) == 0:
                textG = "<b>Guild:</b> <i>None</i>"
            else:
                guild = c.execute("SELECT name FROM Guild WHERE user_id = ?",
                                  (update.effective_message.from_user.id,)).fetchone()[0]
                role = c.execute("SELECT role FROM Guild WHERE user_id = ?",
                                  (update.effective_message.from_user.id,)).fetchone()[0]
                textG = "<b>Guild:</b> <i>" + guild + ' (' + role + ')</i>'

            text = ("Profile of <b>" + nickname + '</b>:\n\n<b>Level:</b> <i>' + str(playerLvl) + ' (' + str(exp) + '/' + str(
                expNeeded) + ')</i>\n<b>Class:</b> <i>' + playerClass + '</i>\n' + '<b>Gold:</b> <i>' + str(
                gold) + '</i>\n<b>Bounty:</b> <i>' + str(
                bounty) + '</i>\n' + textG + '\n_______________\n' + '\n<b>Stats Points:</b> <i>' + str(
                stats_points) + '</i>\n<b>HP:</b> <i>' + str(playerHP) + '/' + str(
                playerHPMax) + '</i>\n<b>Atk:</b> <i>' + str(playerAtk) + ' (+' + str(
                playerAtkBonus) + ')</i>\n<b>Def:</b> <i>' + str(playerDef) + ' (+' + str(playerDefBonus) +
                ')</i>\n<b>Vel:</b> <i>' + str(playerVel) + ' (+' + str(playerVelBonus) + ')</i>\n<b>Crit:</b> <i>' + str(playerCrit) + '%</i>')
            await update.message.reply_text(parse_mode='HTML', text=text)

        else:
            return
        conn.commit()
        conn.close()


async def office(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage first choice of class"""
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

    if await user_is_trading(update):
        await warning_trading_user(update, context)
        return

    user_id = update.effective_message.from_user.id
    userClass = c.execute("SELECT class FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]
    region_id = c.execute("SELECT regionID FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    area_id = c.execute("SELECT areaID FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    type_area = get_area_info(region_id, area_id)[2]
    if type_area == "Not Safe":
        await update.message.reply_text("You can't use this command here! You need to go to a Safe Area!")
        return

    userLvl = c.execute("SELECT lvl FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    if userLvl >= 10:
        if userClass == 'Trainee':
            text = (
             "Welcome to the office, dear adventurer! Here you can choose a personal class, tell me which one will you choose!"
             "\n<i>(Your stats will change according to the chosen class)</i>\n")

            classes = ["Swordsman", "Archer", "Acolyte", "Thief"]
            for class_name in classes:
                class_info = getClass_info(class_name)
                name, hp, atk, def_, vel, crit = class_info
                text += f"\n<b>{name}</b>:\nHP: {hp}\nAtk: {atk}\nDef: {def_}\nVel: {vel}\nCrit: {crit}\n"

            buttonSwordsman = telegram.InlineKeyboardButton(text='Swordsman', callback_data='swordsman')
            buttonArcher = telegram.InlineKeyboardButton(text='Archer', callback_data='archer')
            buttonMage = telegram.InlineKeyboardButton(text='Acolyte', callback_data='acolyte')
            buttonThief = telegram.InlineKeyboardButton(text='Thief', callback_data='thief')
            reply_markup = telegram.InlineKeyboardMarkup(
                [[buttonSwordsman], [buttonArcher], [buttonMage], [buttonThief]])

            await update.message.reply_text(parse_mode='HTML', text=text, reply_markup=reply_markup)

        else:
            text = "You already have done your choice!"
            await update.message.reply_text(parse_mode='HTML', text=text)

    else:
        text = "You don't have the necessary level to be able to change class!"
        await update.message.reply_text(parse_mode='HTML', text=text)

    conn.commit()
    conn.close()


async def office_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage buttons of office function"""
    conn = sqlite3.connect('dungeon.db')
    c = conn.cursor()
    query = update.callback_query
    user_id = query.from_user.id
    cbd = query.data

    class_map = {
        'swordsman': 'Swordsman',
        'archer': 'Archer',
        'acolyte': 'Acolyte',
        'thief': 'Thief'
    }

    if cbd in class_map:
        current_class = c.execute("SELECT class FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]
        if current_class == 'Trainee':
            new_class = class_map[cbd]
            class_info = getClass_info(new_class)
            _, hp, atk, def_, vel, crit = class_info

            current_stats = c.execute("SELECT hp_max, atk, def, vel, crit FROM Profile WHERE user_id = ?",
                                      (user_id,)).fetchone()
            current_hp, current_atk, current_def, current_vel, current_crit = current_stats

            new_hp = current_hp + hp
            new_atk = current_atk + atk
            new_def = current_def + def_
            new_vel = current_vel + vel
            new_crit = current_crit + crit

            c.execute("UPDATE Profile SET class = ? WHERE user_id = ?", (new_class, user_id))
            c.execute(
                "UPDATE Profile SET hp_max = ?, atk = ?, def = ?, vel = ?, crit = ? WHERE user_id = ?",
                (new_hp, new_atk, new_def, new_vel, new_crit, user_id)
            )

            equipped_weapons = c.execute(
                "SELECT id, type FROM Equipment WHERE user_id = ? AND type IN ('Swords', 'Bows', 'Staffs', 'Daggers')",
                (user_id,)).fetchall()
            total_bonus_change = 0
            for weapon_id, weapon_type in equipped_weapons:
                weapon_info = fetch_weapons(weapon_type, 0)
                weapon = next((w for w in weapon_info if w['id'] == weapon_id), None)
                if weapon:
                    allowed_classes = [c.strip() for c in weapon['classes'].split(',')]
                    old_bonus = weapon['attack'] if current_class in allowed_classes else int(weapon['attack'] * 0.4)
                    new_bonus = weapon['attack'] if new_class in allowed_classes else int(weapon['attack'] * 0.4)
                    bonus_difference = new_bonus - old_bonus
                    total_bonus_change += bonus_difference

            c.execute("UPDATE Profile SET atk_bonus = atk_bonus + ? WHERE user_id = ?", (total_bonus_change, user_id))

            text = f"Congratulations, you have become a <b>{new_class}</b>!"
            await query.edit_message_text(parse_mode='HTML', text=text)

        else:
            await context.bot.answer_callback_query(callback_query_id=query.id, text="You have already chosen a class.")

    conn.commit()
    conn.close()