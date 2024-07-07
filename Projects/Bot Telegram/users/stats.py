import telegram
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from utils.helpers import user_registered, user_banned, check_chat, warning_unregistered_user, warning_chat
from asset.asset import get_evolution_info, getClass_info, fetch_weapons

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """allows users to improve determined stats"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    if not await user_registered(update):
        await warning_unregistered_user(update, context)
    else:
        if await check_chat(update):
            await warning_chat(update)
        else:
            if not await user_banned(update):
                stats_points = c.execute("SELECT stats_points FROM Profile WHERE user_id = ?", (update.effective_message.from_user.id,)).fetchone()[0]
                text = "Which stats would you like to upgrade?\n<b>Stats Point:</b> " + str(stats_points)
                buttonHP = telegram.InlineKeyboardButton(text= '+1 HP Max', callback_data= 'hp')
                buttonAtk = telegram.InlineKeyboardButton(text= '+1 Atk', callback_data= 'atk')
                buttonDef = telegram.InlineKeyboardButton(text= '+1 Def', callback_data= 'def')
                buttonVel = telegram.InlineKeyboardButton(text= "+1 Vel", callback_data= 'vel')
                reply_markup= telegram.InlineKeyboardMarkup([[buttonHP], [buttonAtk], [buttonDef], [buttonVel]])
                await update.message.reply_text(parse_mode= 'HTML', text= text, reply_markup= reply_markup)
            else:
                return
            conn.commit()
            conn.close()

async def stats_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage buttons of stats function"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    query = update.callback_query
    cbd = update.callback_query.data
    user_id = update.callback_query.from_user.id
    button_stats = telegram.InlineKeyboardButton(text= 'Stats', callback_data= 'stats')

    if cbd == 'hp':
        if c.execute("SELECT stats_points FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0] >= 1:
            c.execute("UPDATE Profile SET hp_max= (SELECT hp_max FROM Profile WHERE user_id = ?)+1 WHERE user_id = ?;",
                      (user_id, user_id,))
            c.execute("UPDATE Profile SET stats_points = (SELECT stats_points FROM Profile WHERE user_id = ?)-1 WHERE user_id = ?;", (user_id, user_id,))
            text = "You improved your <b>HP</b>!"
            await query.edit_message_text(parse_mode= 'HTML', text=text, reply_markup= telegram.InlineKeyboardMarkup([[button_stats]]))
        else:
            await context.bot.answer_callback_query(callback_query_id=update.callback_query.id, text="You don't have any Stats Point!")
    if cbd == 'atk':
        if c.execute("SELECT stats_points FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0] >= 1:
            c.execute("UPDATE Profile SET atk= (SELECT atk FROM Profile WHERE user_id = ?)+1 WHERE user_id = ?;",
                      (user_id, user_id,))
            c.execute("UPDATE Profile SET stats_points = (SELECT stats_points FROM Profile WHERE user_id = ?)-1 WHERE user_id = ?;", (user_id, user_id,))
            text = "You improved your <b>Atk</b>!"
            await query.edit_message_text(parse_mode= 'HTML', text=text, reply_markup= telegram.InlineKeyboardMarkup([[button_stats]]))
        else:
            await context.bot.answer_callback_query(callback_query_id=update.callback_query.id, text="You don't have any Stats Point!")
    if cbd == 'def':
        if c.execute("SELECT stats_points FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0] >= 1:
            c.execute("UPDATE Profile SET def= (SELECT def FROM Profile WHERE user_id = ?)+1 WHERE user_id = ?;",
                      (user_id, user_id,))
            c.execute("UPDATE Profile SET stats_points = (SELECT stats_points FROM Profile WHERE user_id = ?)-1 WHERE user_id = ?;", (user_id, user_id,))
            text = "You improved your <b>Def</b>!"
            await query.edit_message_text(parse_mode= 'HTML', text=text, reply_markup= telegram.InlineKeyboardMarkup([[button_stats]]))
        else:
            await context.bot.answer_callback_query(callback_query_id=update.callback_query.id,
                                                    text="You don't have any Stats Point!")
    if cbd == 'vel':
        if c.execute("SELECT stats_points FROM Profile WHERE user_id = ?",
                     (user_id,)).fetchone()[0] >= 1:
            c.execute("UPDATE Profile SET vel= (SELECT vel FROM Profile WHERE user_id = ?)+1 WHERE user_id = ?;",
                      (user_id, user_id,))
            c.execute("UPDATE Profile SET stats_points = (SELECT stats_points FROM Profile WHERE user_id = ?)-1 WHERE user_id = ?;",
                      (user_id, user_id,))
            text = "You improved your <b>Vel</b>!"
            await query.edit_message_text(parse_mode='HTML', text=text,
                                          reply_markup=telegram.InlineKeyboardMarkup([[button_stats]]))
        else:
            await context.bot.answer_callback_query(callback_query_id=update.callback_query.id,
                                                    text="You don't have any Stats Point!")
    if cbd == 'stats':
        stats_points = c.execute("SELECT stats_points FROM Profile WHERE user_id = ?",
                                 (user_id,)).fetchone()[0]
        text = "Which stats would you like to upgrade?\n<b>Stats Point:</b> " + str(stats_points)
        buttonHP = telegram.InlineKeyboardButton(text='+1 HP Max', callback_data='hp')
        buttonAtk = telegram.InlineKeyboardButton(text='+1 Atk', callback_data='atk')
        buttonDef = telegram.InlineKeyboardButton(text='+1 Def', callback_data='def')
        buttonVel = telegram.InlineKeyboardButton(text="+1 Vel", callback_data='vel')
        reply_markup = telegram.InlineKeyboardMarkup([[buttonHP], [buttonAtk], [buttonDef], [buttonVel]])
        await query.edit_message_text(parse_mode='HTML', text=text, reply_markup=reply_markup)
    conn.commit()
    conn.close()


async def rankup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage second choice of class and evolution of the chosen one"""
    # Connect to the database
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    user_id = update.callback_query.from_user.id


    try:
        # Retrieve user information
        level = c.execute("SELECT lvl FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
        playerClass = c.execute("SELECT class FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]
        chat_id = c.execute("SELECT chat_id FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]

        # Check for rankup levels
        if level >= 35 and level < 70:
            rankup_classes = ["Knight", "Royal Guard", "Hunter", "Ranger", "Mage", "Alchemist", "Assassin", "Burglar"]
            if playerClass not in rankup_classes:
                text = "Now adventurer, you must choose a path, once chosen... there is no turning back, be careful!\n\n"
                buttons = []

                if playerClass == "Swordsman":
                    text += ("• Knight (Atk+) ↪ Berserker (Atk++, Def-)\n\n"
                             "or\n\n"
                             "• Royal Guard (Def+) ↪ Paladin (Def++, Atk-)")
                    buttons = [
                        InlineKeyboardButton(text="Knight", callback_data="knight"),
                        InlineKeyboardButton(text="Royal Guard", callback_data="royal_guard"),
                    ]
                elif playerClass == "Archer":
                    text += ("• Hunter (Crit+) ↪ Sniper (Crit++, ATK-, Def-)\n\n"
                             "or\n\n"
                             "• Ranger (Exploration Bonus) ↪ Sentinel (Exploration Bonus+, Def-)")
                    buttons = [
                        InlineKeyboardButton(text="Hunter", callback_data="hunter"),
                        InlineKeyboardButton(text="Ranger", callback_data="ranger"),
                    ]
                elif playerClass == "Acolyte":
                    text += ("• Mage (Atk+) ↪ Sorcerer (Atk++, Def--)\n\n"
                             "or\n\n"
                             "• Alchemist (Craft Potion, Atk--) ↪ Sage (Craft Potion+, Def--, Vel--)")
                    buttons = [
                        InlineKeyboardButton(text="Mage", callback_data="mage"),
                        InlineKeyboardButton(text="Alchemist", callback_data="alchemist"),
                    ]
                elif playerClass == "Thief":
                    text += ("Assassin (No damage First Turn) ↪ Shadow (No damage First Turn, Crit+, Def--)\n\n"
                             "or\n\n"
                             "Burglar (Mystery Items Bonus) ↪ Bandit (Mystery Items Bonus, Vel+, Atk-)")
                    buttons = [
                        InlineKeyboardButton(text="Assassin", callback_data="assassin"),
                        InlineKeyboardButton(text="Burglar", callback_data="burglar"),
                    ]

                reply_markup = InlineKeyboardMarkup([buttons])
                await context.bot.send_message(
                    chat_id=chat_id,
                    parse_mode="HTML",
                    text=text,
                    reply_markup=reply_markup,
                )
        elif level >= 70:
            rankup_classes = ["Knight", "Royal Guard", "Hunter", "Ranger", "Mage", "Alchemist", "Assassin", "Burglar"]
            if playerClass in rankup_classes:
                # Check if it's time for automatic evolution
                evolution_info = get_evolution_info(playerClass)
                evolution_name = evolution_info[0]
                evolution_hp, evolution_atk, evolution_def, evolution_vel, evolution_crit = evolution_info[1:]

                current_stats = c.execute("SELECT hp_max, atk, def, vel, crit FROM Profile WHERE user_id = ?",
                                          (user_id,)).fetchone()
                current_hp, current_atk, current_def, current_vel, current_crit = current_stats

                new_hp = current_hp + evolution_hp
                new_atk = current_atk + evolution_atk
                new_def = current_def + evolution_def
                new_vel = current_vel + evolution_vel
                new_crit = current_crit + evolution_crit

                # Automatically evolve the class
                c.execute("UPDATE Profile SET class = ? WHERE user_id = ?", (evolution_name, user_id))
                # Assign the new class stats
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
                        old_bonus = weapon['attack'] if playerClass in allowed_classes else int(
                            weapon['attack'] * 0.4)
                        new_bonus = weapon['attack'] if evolution_name in allowed_classes else int(weapon['attack'] * 0.4)
                        bonus_difference = new_bonus - old_bonus
                        total_bonus_change += bonus_difference

                c.execute("UPDATE Profile SET atk_bonus = atk_bonus + ? WHERE user_id = ?",
                          (total_bonus_change, user_id))

                message = f"Congratulations, you have become a <b>{evolution_name}</b>!"
                await context.bot.send_message(
                    chat_id=chat_id,
                    parse_mode="HTML",
                    text=message,
                )

    except Exception as e:
        print(f"Error during rankup: {e}")

    finally:
        # Commit changes and close connection
        conn.commit()
        conn.close()


async def rankup_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage buttons of rankup function"""
    # Connect to the database
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    try:
        # Retrieve data from callback query
        query = update.callback_query
        callback_data = query.data
        user_id = query.from_user.id

        current_class = c.execute("SELECT class FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]

        # Determine the new class based on callback data
        if callback_data == "knight":
            new_class = "Knight"
            message = "Congratulations, you have become a <b>Knight</b>!"
        elif callback_data == "royal_guard":
            new_class = "Royal Guard"
            message = "Congratulations, you have become a <b>Royal Guard</b>!"
        elif callback_data == "hunter":
            new_class = "Hunter"
            message = "Congratulations, you have become a <b>Hunter</b>!"
        elif callback_data == "ranger":
            new_class = "Ranger"
            message = "Congratulations, you have become a <b>Ranger</b>!"
        elif callback_data == "mage":
            new_class = "Mage"
            message = "Congratulations, you have become a <b>Mage</b>"
        elif callback_data == "alchemist":
            new_class = "Alchemist"
            message = "Congratulations, you have become a <b>Alchemist</b>!"
        elif callback_data == "assassin":
            new_class = "Assassin"
            message = "Congratulations, you have become a <b>Assassin</b>!"
        elif callback_data == "burglar":
            new_class = "Burglar"
            message = "Congratulations, you have become a <b>Burglar</b>!"

        # Get the stats for the new class
        class_stats = getClass_info(new_class)
        _, hp, atk, def_, vel, crit = class_stats

        current_stats = c.execute("SELECT hp_max, atk, def, vel, crit FROM Profile WHERE user_id = ?",
                                      (user_id,)).fetchone()
        current_hp, current_atk, current_def, current_vel, current_crit = current_stats

        new_hp = current_hp + hp
        new_atk = current_atk + atk
        new_def = current_def + def_
        new_vel = current_vel + vel
        new_crit = current_crit + crit

        # Update class and stats in the database
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

        c.execute("UPDATE Profile SET atk_bonus = atk_bonus + ? WHERE user_id = ?",
                  (total_bonus_change, user_id))
        await query.edit_message_text(
            parse_mode="HTML",
            text=message,
        )

    except Exception as e:
        print(f"Error during rankup_cb: {e}")

    finally:
        # Commit changes and close connection
        conn.commit()
        conn.close()


async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """checks if user has enough exp to earn a level"""
    # Connect to the database
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    user_id = update.callback_query.from_user.id

    try:
        # Retrieve user information
        level = c.execute(
            "SELECT lvl FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
        expNeeded = level * 50
        exp = c.execute("SELECT exp FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
        nickname = c.execute("SELECT nickname FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]

        # Handle level upgrade logic (assuming it's correct)
        if exp >= expNeeded:
            exp_persa = exp - expNeeded
            exp = expNeeded
            if exp / expNeeded == 1:
                c.execute("UPDATE User SET lvl = lvl + 1, exp = exp - ? WHERE user_id = ?",
                          (exp, user_id,))
                c.execute("UPDATE User SET exp = exp + ? WHERE user_id = ?",
                    (exp_persa, user_id,))
                playerHPMax = c.execute("SELECT hp_max FROM Profile WHERE user_id = ?",
                                        (user_id,)).fetchone()[0]
                c.execute("UPDATE Profile SET hp = ?, stats_points = stats_points + 3 WHERE user_id = ?",
                          (playerHPMax, user_id,))
                text = f"{nickname}, you leveled up! \n<i>(Use /stats to upgrade your stats!)</i>"
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    parse_mode="HTML",
                    text=text
                )

        # Call rankup function (assuming it's not asynchronous)
        await rankup(update, context)

    except Exception as e:
        print(f"Error during upgrade: {e}")

    finally:
        # Commit changes and close connection
        conn.commit()
        conn.close()