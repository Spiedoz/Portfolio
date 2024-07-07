import sqlite3
import random
from telegram import Update
from asset.asset import fetch_monsterID, fetch_itemID, get_item_info, get_area_info
from events.rarity import getrarity, itemsRarity

async def exploreDraws(update: Update) -> int:
    """extraction of what event will happen in the dungeon"""
    global mostro_random
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    user_id = update.effective_message.from_user.id
    user_regionID = c.execute("SELECT regionID FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    user_area_ID = c.execute("SELECT areaID FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    user_class = c.execute("SELECT class FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]

    # bonus classes
    if user_class == "Ranger":
        monster_chance = 90
        item_chance = 7
    elif user_class == "Sentinel":
        monster_chance = 88
        item_chance = 9
    else:
        monster_chance = 93
        item_chance = 3

    draw = random.randint(1, 100)

    # monster event
    if draw <= monster_chance:
        monstersList = []
        monsterRarity = getrarity()
        monstersID = fetch_monsterID(user_regionID, user_area_ID, monsterRarity)
        for monsters in monstersID:
            if isinstance(monsters, tuple):
                monstersList.append(monsters[0])
            else:
                monstersList.append(monsters)

        randomMonsterID = random.choice(monstersList)

    # item event
    elif draw <= (monster_chance + item_chance):
        randomMonsterID = 0
        itemsList = []
        itemRarity = itemsRarity()
        itemsID = fetch_itemID(user_regionID, user_area_ID, itemRarity)
        for items in itemsID:
            if isinstance(items, tuple):
                itemsList.append(items[0])
            else:
                itemsList.append(items)

        if len(itemsList) == 0:
            text = "You found nothing.."
            await update.message.reply_text(parse_mode='HTML', text=text)
        else:
            randomItemID = random.choice(itemsList)
            itemName, itemRarity, itemType = get_item_info(randomItemID)
            if c.execute("SELECT COUNT(*) FROM Inventory WHERE user_id = ? and id = ? and type = ?", (user_id, randomItemID, itemType)).fetchone()[0] == 0:
                c.execute("INSERT INTO Inventory (user_id, id, name, rarity, type, qt) VALUES (?, ?, ?, ?, ?, ?)",
                          (user_id, randomItemID, itemName, itemRarity, itemType, 1))
            else:
                c.execute("UPDATE Inventory SET qt = (SELECT qt FROM Inventory WHERE user_id = ? AND id = ? and type = ?)+? WHERE user_id = ? AND id = ? and type = ?",
                          (user_id, randomItemID, itemType, 1, user_id, randomItemID, itemType))

            areaName = get_area_info(user_regionID, user_area_ID)[1]
            text = f"You found a <i>{itemName} [{itemRarity}]</i> as you wandered around <b>{areaName}</b>!"
            await update.message.reply_text(parse_mode='HTML', text=text)
    # no event
    else:
        randomMonsterID = 0
        text = "You found nothing.."
        await update.message.reply_text(parse_mode='HTML', text=text)

    conn.commit()
    conn.close()
    return randomMonsterID
