import telegram
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from asset.asset import fetch_weapons, fetch_shields, get_area_info
from utils.helpers import (user_registered, user_banned, check_chat, user_is_trading,
                           warning_unregistered_user, warning_chat, warning_unsafe, warning_trading_user)

TAVERN_OPTIONS = {
    1: {  # Reign of Mythic - Main Square
        "name": "Main Square Tavern",
        "option1": {"name": "Mythic Mead", "cost": 30, "hp_gain": 15},
        "option2": {"name": "Legend's Feast", "cost": 220, "full_heal": True}
    },
    2: {  # Burning Lands of Ignis - Cold Stone Town
        "name": "Frostfire Inn",
        "option1": {"name": "Chilled Lava Shot", "cost": 35, "hp_gain": 20},
        "option2": {"name": "Ignis Ice Bath", "cost": 240, "full_heal": True}
    },
    3: {  # Desertia - Dark Sand Village
        "name": "Oasis Retreat",
        "option1": {"name": "Sand Berry Juice", "cost": 40, "hp_gain": 25},
        "option2": {"name": "Mirage Massage", "cost": 260, "full_heal": True}
    },
    4: {  # Tempest Islands - Shell Harbor
        "name": "Stormy Seashell Tavern",
        "option1": {"name": "Tempest Tonic", "cost": 45, "hp_gain": 30},
        "option2": {"name": "Whirlpool Therapy", "cost": 280, "full_heal": True}
    },
    5: {  # Eternal Forest - LivingGreen Village
        "name": "Evergreen Elixir Bar",
        "option1": {"name": "Forest Fairy Fizz", "cost": 50, "hp_gain": 35},
        "option2": {"name": "Dryad's Embrace", "cost": 300, "full_heal": True}
    }
}


async def tavern(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """offers a way to heal the user"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    if not await user_registered(update):
        await warning_unregistered_user(update, context)
        return

    if await check_chat(update):
        await warning_chat(update)

    if await user_banned(update):
        return

    if await user_is_trading(update):
        await warning_trading_user(update, context)
        return

    user_id = update.effective_message.from_user.id
    nickname = c.execute("SELECT nickname FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    region_id = c.execute("SELECT regionID FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    area_id = c.execute("SELECT areaID FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    type_area = get_area_info(region_id, area_id)[2]

    if type_area == 'Not Safe':
        await warning_unsafe(update)
        return
    else:
        tavern_info = TAVERN_OPTIONS.get(region_id, TAVERN_OPTIONS[1])  # Default to Reign of Mythic if not found
        text = f"Welcome <b>{nickname}</b> to the {tavern_info['name']}! Here we offer:\n\n"
        text += (f"1. {tavern_info['option1']['name']} <i>(+{tavern_info['option1']['hp_gain']} HP)</i> for "
                 f"<b>{tavern_info['option1']['cost']} gold</b>\n")
        text += f"2. {tavern_info['option2']['name']} <i>(Full Heal)</i> for <b>{tavern_info['option2']['cost']} gold</b>\n\n"
        text += "How would you like to rest?"

        button1 = telegram.InlineKeyboardButton(
            text=f"{tavern_info['option1']['name']} ({tavern_info['option1']['cost']} gold)",
            callback_data=f"tavern_option1_{region_id}")
        button2 = telegram.InlineKeyboardButton(
            text=f"{tavern_info['option2']['name']} ({tavern_info['option2']['cost']} gold)",
            callback_data=f"tavern_option2_{region_id}")
        reply_markup = telegram.InlineKeyboardMarkup([[button1], [button2]])
        await update.message.reply_text(parse_mode='HTML', text=text, reply_markup=reply_markup)

        conn.commit()
        conn.close()


async def tavern_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage buttons of tavern function"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    cbd = update.callback_query.data
    user_id = update.callback_query.from_user.id

    playerHPMax = c.execute("SELECT hp_max FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]
    current_gold = c.execute("SELECT gold FROM User WHERE user_id = ?", (str(user_id),)).fetchone()[0]

    option, region_id = cbd.split('_')[1:]
    region_id = int(region_id)
    tavern_info = TAVERN_OPTIONS.get(region_id, TAVERN_OPTIONS[1])

    if option == 'option1':
        price = tavern_info['option1']['cost']
        hp_gain = tavern_info['option1']['hp_gain']
        if current_gold >= price:
            c.execute("UPDATE User SET gold = gold - ? WHERE user_id = ?", (price, user_id))
            c.execute("UPDATE Profile SET hp = MIN(hp + ?, ?) WHERE user_id = ?", (hp_gain, playerHPMax, user_id))
            text = f"You enjoyed a refreshing <b>{tavern_info['option1']['name']}</b> and gained <i>{hp_gain} HP</i>!"
        else:
            await context.bot.answer_callback_query(callback_query_id=update.callback_query.id,
                                                    text="You don't have enough gold!")
            return
    elif option == 'option2':
        price = tavern_info['option2']['cost']
        if current_gold >= price:
            c.execute("UPDATE User SET gold = gold - ? WHERE user_id = ?", (price, user_id))
            c.execute("UPDATE Profile SET hp = ? WHERE user_id = ?", (playerHPMax, user_id))
            text = f"You indulged in the <b>{tavern_info['option2']['name']}</b> and fully recovered your HP!"
        else:
            await context.bot.answer_callback_query(callback_query_id=update.callback_query.id,
                                                    text="You don't have enough gold!")
            return

    await context.bot.deleteMessage(message_id=update.callback_query.message.message_id,
                                    chat_id=update.callback_query.message.chat.id)
    await context.bot.send_message(chat_id=update.callback_query.message.chat.id, parse_mode='HTML', text=text)

    conn.commit()
    conn.close()



# Armory
ARMORY_INTROS = {
    1: "Welcome to the <b>Mythic Forge</b>! Our weapons are infused with the essence of legends.",
    2: "Step into the <b>Flames Armory</b>! Our weapons are forged in the hottest fires of Ignis.",
    3: "Enter the <b>Sandstorm Bazaar</b>! Our weapons are as resilient as the desert itself.",
    4: "Welcome to the <b>Tempest Arsenal</b>! Our weapons harness the power of storms.",
    5: "Behold the <b>Evergreen Armory</b>! Our weapons are blessed by the spirits of the forest.",
}

# Categories of weapons
WEAPON_CATEGORIES = ["Swords", "Bows", "Daggers", "Wands", "Shields"]


async def armory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """allows users to gain atk or def"""
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
    region_id = c.execute("SELECT regionID FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    area_id = c.execute("SELECT areaID FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    type_area = get_area_info(region_id, area_id)[2]

    conn.close()

    if type_area == 'Not Safe':
        await warning_unsafe(update)
        return
    else:
        intro_text = ARMORY_INTROS.get(region_id, ARMORY_INTROS[1])
        text = f"{intro_text}\n\nWhat would you like to see?"

        buttons = [[InlineKeyboardButton(category, callback_data=f"armory_category_{category}_{region_id}")
                    for category in WEAPON_CATEGORIES]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(parse_mode='HTML', text=text, reply_markup=reply_markup)


async def armory_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage buttons of armory function"""
    query = update.callback_query
    cbd = query.data

    if cbd.startswith('armory_category_'):
        _, _, category, region_id = cbd.split('_')
        await show_category_items(update, context, category, int(region_id))
    elif cbd.startswith('armory_item_'):
        _, _, item_id, category, region_id = cbd.split('_')
        await show_item_details(update, context, int(item_id), category, int(region_id))
    elif cbd.startswith('buy_item_'):
        _, _, item_id, category, region_id = cbd.split('_')
        await buy_item(update, context, int(item_id), category, int(region_id))
    elif cbd == 'back_to_armory':
        await show_armory_menu(update, context)


async def show_category_items(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, region_id: int):
    """shows the options available basing on the chosen category"""
    if category == 'Shields':
        items = fetch_shields(region_id)
    else:
        items = fetch_weapons(category, region_id)

    buttons = [[InlineKeyboardButton(f"{item['name']} - {item['price']} gold",
                                     callback_data=f"armory_item_{item['id']}_{category}_{region_id}")] for item in
               items]
    buttons.append([InlineKeyboardButton("Back to Armory", callback_data="back_to_armory")])
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.callback_query.edit_message_text(
        text=f"Available <b>{category}</b> in this region:",
        reply_markup=reply_markup, parse_mode='HTML'
    )


async def show_item_details(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: int, category: str,
                            region_id: int):
    """shows details of the selected items"""
    if category == 'Shields':
        items = fetch_shields(region_id)
    else:
        items = fetch_weapons(category, region_id)

    item = next((item for item in items if item['id'] == item_id), None)
    if not item:
        await update.callback_query.answer("Item not found!", show_alert=True)
        return

    if category == 'Shields':
        text = (
            f"<b>{item['name']}</b> [#{item['id']}]\n\n"
            f"<b>Defense:</b> <i>{item['defense']}</i>\n"
            f"<b>Price:</b> <i>{item['price']}</i>\n"
            f"<b>Rarity:</b> <i>{item['rarity']}</i>\n\n"
            "Do you want to buy this item?"
        )
    else:
        text = (
            f"<b>{item['name']}</b> [#{item['id']}]\n\n"
            f"<b>Attack:</b> <i>{item['attack']}</i>\n"
            f"<b>Price:</b> <i>{item['price']}</i>\n"
            f"<b>Class:</b> <i>{item['classes']}</i>\n"
            f"<b>Rarity:</b> <i>{item['rarity']}</i>\n\n"
            "Do you want to buy this item?"
        )

    buttons = [
        [InlineKeyboardButton("Buy", callback_data=f"buy_item_{item_id}_{category}_{region_id}")],
        [InlineKeyboardButton("Back to Armory", callback_data="back_to_armory")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await update.callback_query.edit_message_text(
        parse_mode='HTML',
        text=text,
        reply_markup=reply_markup
    )


async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: int, category: str, region_id: int):
    """manage the buying of the weapons or shield"""
    query = update.callback_query

    conn = sqlite3.connect('dungeon.db')
    c = conn.cursor()
    user_id = query.from_user.id

    if category == 'Shields':
        items = fetch_shields(region_id)
    else:
        items = fetch_weapons(category, region_id)

    item = next((item for item in items if item['id'] == item_id), None)
    if not item:
        await query.answer("Item not found!", show_alert=True)
        conn.close()
        return

    name = item['name']
    price = item['price']
    rarity = item['rarity']

    c.execute("SELECT gold FROM User WHERE user_id = ?", (user_id,))
    user_gold = c.fetchone()[0]

    if user_gold < price:
        await context.bot.answer_callback_query(callback_query_id=update.callback_query.id,
                                                text="You don't have enough gold!")
        conn.close()
        return

    c.execute("UPDATE User SET gold = gold - ? WHERE user_id = ?", (price, user_id))

    c.execute("SELECT qt FROM Inventory WHERE user_id = ? AND id = ? and type = ?", (user_id, item_id, category,))
    existing_item = c.fetchone()

    if existing_item:
        c.execute("UPDATE Inventory SET qt = qt + 1 WHERE user_id = ? AND id = ? and type = ?",
                  (user_id, item_id, category,))
    else:
        c.execute("INSERT INTO Inventory (user_id, id, name, rarity, type, qt) VALUES (?, ?, ?, ?, ?, 1)",
                  (user_id, item_id, name, rarity, category))

    conn.commit()
    conn.close()

    await context.bot.answer_callback_query(callback_query_id=update.callback_query.id,
                                            text=f"You have successfully purchased {name}!")

    text = f"You have purchased <b>{name}</b>.\nDo you want to buy anything else?"
    buttons = [
        [InlineKeyboardButton("Back to Armory", callback_data="back_to_armory")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='HTML')


async def show_armory_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """shows the main menu of the armory"""
    query = update.callback_query
    conn = sqlite3.connect('dungeon.db')
    c = conn.cursor()
    user_data = c.execute("SELECT nickname, regionID FROM User WHERE user_id = ?", (query.from_user.id,)).fetchone()
    conn.close()

    if not user_data:
        await query.edit_message_text("Error: User data not found.")
        return

    nickname, region_id = user_data
    intro_text = ARMORY_INTROS.get(region_id, ARMORY_INTROS[1])
    text = f"{intro_text}\n\nWhat would you like to see?"

    buttons = [[InlineKeyboardButton(category, callback_data=f"armory_category_{category}_{region_id}") for category in
                WEAPON_CATEGORIES]]
    reply_markup = InlineKeyboardMarkup(buttons)

    await query.edit_message_text(parse_mode='HTML', text=text, reply_markup=reply_markup)