import sqlite3
import random
from telegram import InlineKeyboardButton, KeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from asset.asset import get_monster_info, get_region_info, get_area_info, fetch_regions, fetch_areas
from events.encounters import exploreDraws
from utils.helpers import (check_chat, user_banned, user_registered, user_is_battling, user_is_trading,
                           warning_unregistered_user, warning_chat, warning_trading_user, warning_battling_user, warning_safe)


async def clear(update: Update) -> None:
    """delete monsters to light the database"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    c.execute("DELETE FROM '{}'".format(update.effective_message.from_user.id))
    conn.commit()
    conn.close()


async def travel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """allow user to change region and area"""
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

    if await user_is_battling(update):
        await warning_battling_user(update, context)
        return

    if await user_is_trading(update):
        await warning_trading_user(update, context)
        return

    user_id = update.effective_message.from_user.id
    playerLvl = c.execute("SELECT lvl FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    playerRegion = c.execute("SELECT regionID FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    regionName = get_region_info(playerRegion)[0][1]
    regions = fetch_regions()

    keyboard = []
    for region in regions:
        region_id, name, min_lvl, callback = region
        if playerLvl >= min_lvl:
            keyboard.append([InlineKeyboardButton(name, callback_data=callback)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Choose a Region to travel to:\n\n(Current Region: <b>{regionName}</b>)",
                                    reply_markup=reply_markup, parse_mode='HTML')


async def travel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage buttons of the travel function"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    query = update.callback_query
    user_id = query.from_user.id

    playerLvl = c.execute("SELECT lvl FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    playerRegion = c.execute("SELECT regionID FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    playerArea = c.execute("SELECT areaID FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    areaName = get_area_info(playerRegion, playerArea)[1]

    if query.data.startswith("R"):
        region_id = int(query.data[1:])
        region_info = get_region_info(region_id)[0]
        region_name = region_info[1]

        areas = fetch_areas(region_id)
        keyboard = []
        for area in areas:
            area_id, name, min_lvl, callback = area
            if playerLvl >= min_lvl:
                keyboard.append([InlineKeyboardButton(name, callback_data=callback)])

        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Dungeons available in <b>{region_name}</b>:\n\n(Current Dungeon: <b>{areaName}</b>)",
                                          reply_markup=reply_markup, parse_mode='HTML')
        else:
            await query.edit_message_text(f"There are no dungeons available for your level in {region_name}.")

    elif query.data.startswith("A"):
        area_callback = query.data
        region_id = int(area_callback[-1])  # L'ultimo carattere è l'ID della regione
        area_id = int(area_callback[1])  # Il secondo carattere è l'ID dell'area
        area_name = get_area_info(region_id, area_id)[1]
        area_type = get_area_info(region_id, area_id)[2]
        playerStatus = "idle" if area_type == "Safe" else "exploring"
        c.execute("UPDATE Profile SET status = ? WHERE user_id = ?", (playerStatus, user_id,))
        c.execute("UPDATE User SET regionID = ? , areaID = ? WHERE user_id = ?", (region_id, area_id, user_id,))
        await query.edit_message_text(f"You have reached the meanders of <b>{area_name}</b>.", parse_mode='HTML')

    else:
        await query.answer("Callback not recognized.")

    conn.commit()
    conn.close()

async def explore(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage the exploration within the area selected"""
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

    if await user_is_battling(update):
        await warning_battling_user(update, context)
        return

    if await user_is_trading(update):
        await warning_trading_user(update, context)
        return

    user_id = update.effective_message.from_user.id
    region_id = c.execute("SELECT regionID FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    area_id = c.execute("SELECT areaID FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    type_area = get_area_info(region_id, area_id)[2]

    if type_area == 'Safe':
        await warning_safe(update)
        return

    monster_id = await exploreDraws(update)
    if monster_id == 0:
        return


    c.execute(
            f"CREATE TABLE IF NOT EXISTS '{user_id}' (monster_id INTEGER NOT NULL, name TEXT NOT NULL, lvl INTEGER NOT NULL,"
            f"rarity TEXT NOT NULL, hp INTEGER NOT NULL, hp_max INTEGER NOT NULL, atk INTEGER NOT NULL, def INTEGER NOT NULL,"
            f"vel INTEGER NOT NULL, crit INTEGER NOT NULL, regionID INTEGER NOT NULL, areaID INTEGER NOT NULL);"
    )

    # generate monster stats
    (monsterName, monsterPhoto, monsterLvls, monsterRarity, monsterHPs, monsterAtks,
    monsterDefs, monsterVels, monsterCrits, monsterRegion, monsterArea) = get_monster_info(monster_id)

    monsterLvl = random.randint(monsterLvls[0], monsterLvls[1])
    monsterHP = random.randint(monsterHPs[0], monsterHPs[1])
    monsterHPMax = monsterHP
    monsterAtk = random.randint(monsterAtks[0], monsterAtks[1])
    monsterDef = random.randint(monsterDefs[0], monsterDefs[1])
    monsterVel = random.randint(monsterVels[0], monsterVels[1])
    monsterCrit = random.randint(monsterCrits[0], monsterCrits[1])

    randomMonsterID = 1
    while c.execute(f"SELECT * FROM '{user_id}' WHERE monster_id = ?", (randomMonsterID,)).fetchall():
        randomMonsterID += 1
        if randomMonsterID >= 5:
            await clear(update)
            randomMonsterID = 1
            break

    if c.execute("SELECT COUNT(*) FROM Duel WHERE user_id = ?", (user_id,)).fetchone()[0] == 0:
        c.execute("INSERT INTO Duel(user_id, monster_id, message_id, turn) VALUES (?, ?, ?, ?)", (user_id, randomMonsterID, "Null", 1))
    else:
        c.execute("UPDATE Duel SET monster_id = ?, turn = ? WHERE user_id = ?", (randomMonsterID, 1, user_id,))

    c.execute(f"INSERT INTO '{user_id}'(monster_id, name, lvl, rarity, hp, hp_max, atk, def, vel, crit, regionID,"
              f"areaID) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    (randomMonsterID, monsterName, monsterLvl, monsterRarity, monsterHP, monsterHPMax, monsterAtk, monsterDef,
     monsterVel, monsterCrit, monsterRegion, monsterArea))

    conn.commit()
    conn.close()

    if monsterRarity == 'SR':
        text = "You managed to spot the Boss of this dungeon!\n"
    else:
        text = ""

    text += (
        f"You ran into a <b>{monsterName}</b> (Lvl. {monsterLvl})\n\n"
        f"<i>HP: {monsterHP}\nAttack: {monsterAtk}\nDefence: {monsterDef}\n"
        f"Speed: {monsterVel}</i>\n\n"
        "To engage in battle use /battle\nTo keep exploring use /explore"
    )

    travel = KeyboardButton(text="/travel")
    explore = KeyboardButton(text="/explore")
    battle = KeyboardButton(text="/battle")
    reply_markup = ReplyKeyboardMarkup(keyboard=[[explore, battle], [travel]], resize_keyboard=True, selective=True)

    await context.bot.send_photo(chat_id=update.effective_message.chat.id,
                                parse_mode='HTML',
                                caption=text,
                                reply_to_message_id=update.message.message_id,
                                photo=monsterPhoto,
                                reply_markup=reply_markup)
