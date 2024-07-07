import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from asset.asset import inspect_item, fetch_weapons, fetch_shields, get_potion_info, get_item_id, get_potion, get_potion_bonus
from events.rarity import calculate_heal_amount, generate_mystery_reward
from utils.helpers import (user_is_trading, user_registered, user_banned, check_chat, warning_trading_user,
                           warning_unregistered_user, warning_chat)


async def inventory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """shows items of user"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    if not await user_registered(update):
        await warning_unregistered_user(update, context)
    else:
        if not await user_banned(update):
            nickname = c.execute("SELECT nickname FROM User WHERE user_id = ?",
                                 (update.effective_message.from_user.id,)).fetchone()[0]
            text = "<b>" + nickname + "</b>'s inventory: <i>(Page 1)</i>\n\n"
            items = c.execute("SELECT * FROM Inventory WHERE user_id = ? LIMIT 20",
                                (update.effective_message.from_user.id,)).fetchall()
            if len(items) == 0:
                text = "Your inventory is empty, start exploring for new items!"
                await update.message.reply_text(parse_mode='HTML', text=text)
            else:
                i = 1
                for item in items:
                    text += str(i) + ") <b>" + item[2] + "</b> (" + item[3] + ") <i>x" + str(
                        item[5]) + "</i>\n"
                    i += 1
                kb = [[InlineKeyboardButton(text='Page 2 >', callback_data='page:2')]]
                await update.message.reply_text(parse_mode='HTML', text=text, reply_markup=InlineKeyboardMarkup(kb))
            conn.commit()
            conn.close()
        else:
            return


async def inventory_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manages pages of inventory function"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    query = update.callback_query
    page = int(update.callback_query.data.split(':', 1)[1])
    offset = (page - 1) * 20
    nickname = c.execute("SELECT nickname FROM User WHERE user_id = ?",
                         (update.callback_query.from_user.id,)).fetchone()[0]
    text = "<b>" + nickname + "</b>'s inventory: <i>(Page " + str(page) + ")</i>\n\n"
    items = c.execute("SELECT * FROM Inventory WHERE user_id = ? LIMIT 20 OFFSET ?",
                        (update.callback_query.from_user.id, offset,)).fetchall()
    if len(items) > 0:
        if page == 1:
            i = 1
        else:
            i = 1 + offset
        for item in items:
            text += str(i) + ") <b>" + item[2] + "</b> (" + item[3] + ") <i>x" + str(
                item[5]) + "</i>\n"
            i += 1
        kb = []
        if page > 1:
            kb.append(InlineKeyboardButton(text='< Page ' + str(page - 1), callback_data='page:' + str(page - 1)))
        kb.append(InlineKeyboardButton(text='Page ' + str(page + 1) + ' >', callback_data='page:' + str(page + 1)))
        await query.edit_message_text(parse_mode='HTML', text=text, reply_markup=InlineKeyboardMarkup([kb]))
    else:
        await context.bot.answer_callback_query(callback_query_id=update.callback_query.id,
                                                text="There is nothing more to see!")


weapons = ["Swords", "Bows", "Daggers", "Wands"]

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """shows details of the specified item"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    if not await user_registered(update):
        await warning_unregistered_user(update, context)
    else:
        if await check_chat(update):
            await warning_chat(update)
        else:
            if not await user_banned(update):
                try:
                    item_index = int(update.effective_message.text.split(' ', 1)[1]) - 1
                except:
                    await update.message.reply_text("Please provide a valid item number.")
                    return

                user_id = update.effective_message.from_user.id
                items = c.execute("SELECT * FROM Inventory WHERE user_id = ?",
                                    (user_id,)).fetchall()

                if 0 <= item_index < len(items):
                    item = items[item_index]
                    item_id = item[1]
                    item_type = item[4]
                    item_qt = item[5]

                    text = ""

                    if item_type in weapons:
                        item_info = fetch_weapons(item_type)
                        item = next((i for i in item_info if i['id'] == item_id), None)
                        if item:
                            text = f"{item['name']}\n\n<b>Value:</b> <i>{int(item['price']/2)}</i>\n<b>Rarity:</b> <i>{item['rarity']}</i>\n<b>Type:</b> <i>{item_type}</i>\n<b>Attack:</b> <i>{item['attack']}</i>\n<b>Classes:</b> <i>{item['classes']}</i>\n<b>Quantity:</b> <i>{item_qt}</i>"
                    elif item_type == 'Shields':
                        item_info = fetch_shields()
                        item = next((i for i in item_info if i['id'] == item_id), None)
                        if item:
                            text = f"{item['name']}\n\n<b>Value:</b> <i>{int(item['price']/2)}</i>\n<b>Rarity:</b> <i>{item['rarity']}</i>\n<b>Type:</b> <i>{item_type}</i>\n<b>Defense:</b> <i>{item['defense']}</i>\n<b>Quantity:</b> <i>{item_qt}</i>"
                    elif item_type.startswith('Potion'):
                        itemName, itemRarity, itemType, itemPrice = get_potion(item_id)
                        text = f"{itemName}\n\n<b>Value:</b> <i>{itemPrice}</i>\n<b>Rarity:</b> <i>{itemRarity}</i>\n<b>Type:</b> <i>{itemType}</i>\n<b>Quantity:</b> <i>{item_qt}</i>"
                    else:
                        itemName, itemRarity, itemPrice, itemType = inspect_item(item_id)
                        text = f"{itemName}\n\n<b>Value:</b> <i>{itemPrice}</i>\n<b>Rarity:</b> <i>{itemRarity}</i>\n<b>Type:</b> <i>{itemType}</i>\n<b>Quantity:</b> <i>{item_qt}</i>"

                    await update.message.reply_text(parse_mode='HTML', text=text)
                else:
                    text = "Invalid item number or you don't own this item!"
                    await update.message.reply_text(parse_mode='HTML', text=text)
                conn.commit()
                conn.close()
            else:
                return


async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage the sale of the specified item"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    if not await user_registered(update):
        await warning_unregistered_user(update, context)
    else:
        if not await user_banned(update):
            try:
                item_index = int(update.message.text.split(' ', 2)[1]) - 1
            except:
                await update.message.reply_text("Please provide a valid item number.")
                return
            try:
                qt = int(update.effective_message.text.split(' ', 2)[2])
            except:
                qt = 1

            if qt <= 0:
                await update.message.reply_text("Please provide a valid quantity.")
                return

            user_id = update.effective_message.from_user.id
            items = c.execute("SELECT * FROM Inventory WHERE user_id = ?", (user_id,)).fetchall()

            if 0 <= item_index < len(items):
                item = items[item_index]
                item_id = item[1]
                item_type = item[4]
                item_quantity = item[5]

                if item_quantity >= qt:
                    # Check if the item is equipped
                    equipped = c.execute("SELECT * FROM Equipment WHERE user_id = ? AND id = ? AND type = ?",
                                         (user_id, item_id, item_type)).fetchone()
                    if equipped and item_quantity == 1:
                        await update.message.reply_text("You can't sell an equipped item!")
                    else:
                        if item_type in weapons:
                            item_info = fetch_weapons(item_type, 0)
                            item = next((i for i in item_info if i['id'] == item_id), None)
                            if item:
                                itemName = item['name']
                                itemPrice = item['price']/2
                        elif item_type == 'Shields':
                            item_info = fetch_shields(0)
                            item = next((i for i in item_info if i['id'] == item_id), None)
                            if item:
                                itemName = item['name']
                                itemPrice = item['price']/2
                        elif item_type.startswith("Potion"):
                            itemName, _, _, itemPrice = get_potion(item_id)
                        else:
                            itemName, _, itemPrice, _ = inspect_item(item_id)

                        value = int(int(itemPrice) * qt)
                        c.execute("UPDATE User SET gold = gold + ? WHERE user_id = ?", (value, user_id))
                        c.execute("UPDATE Inventory SET qt = qt - ? WHERE user_id = ? AND id = ? and type = ?",
                                  (qt, user_id, item_id, item_type))

                        if item_quantity - qt == 0:
                            c.execute("DELETE FROM Inventory WHERE user_id = ? AND id = ? and type = ?",
                                      (user_id, item_id, item_type,))

                        text = f"You sold <b>{qt} {itemName}</b> <i>(+{value} gold)</i>"
                        await update.message.reply_text(parse_mode='HTML', text=text)
                else:
                    await update.message.reply_text("You don't have the quantity specified by you!")
            else:
                await update.message.reply_text("Invalid item number or you don't own this item!")

            conn.commit()
            conn.close()
        else:
            return


async def equip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """allows users to equip weapons and shields"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    if not await user_registered(update):
        await warning_unregistered_user(update, context)
    else:
        if not await user_banned(update):
            try:
                item_index = int(update.message.text.split(' ', 1)[1]) - 1
            except:
                await update.message.reply_text("Please provide a valid item number.")
                return

            user_id = update.effective_message.from_user.id
            items = c.execute("SELECT * FROM Inventory WHERE user_id = ?", (user_id,)).fetchall()

            if 0 <= item_index < len(items):
                item = items[item_index]
                item_id = item[1]
                item_type = item[4]

                # Get user's class
                playerClass = c.execute("SELECT class FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]

                if item_type in weapons or item_type == 'Shields':
                    # Check if an item of the same type is already equipped
                    equipped = c.execute("SELECT * FROM Equipment WHERE user_id = ? AND type = ?",
                                         (user_id, item_type)).fetchone()

                    if equipped:
                        await update.message.reply_text(f"You already have some <b>{item_type}</b> equipped. Disequip it first.",
                                                        parse_mode='HTML')
                    else:
                        # Equip the item
                        c.execute("INSERT INTO Equipment (user_id, id, type) VALUES (?, ?, ?)",
                                  (user_id, item_id, item_type))

                        # Update bonus in Profile
                        if item_type in weapons:
                            item_info = fetch_weapons(item_type, 0)
                            item = next((i for i in item_info if i['id'] == item_id), None)
                            if item:
                                allowed_classes = [c.strip() for c in item['classes'].split(',')]
                                bonus = item['attack'] if playerClass in allowed_classes else int(item['attack'] * 0.4)
                                c.execute("UPDATE Profile SET atk_bonus = atk_bonus + ? WHERE user_id = ?",
                                          (bonus, user_id))
                        elif item_type == 'Shields':
                            item_info = fetch_shields(0)
                            item = next((i for i in item_info if i['id'] == item_id), None)
                            if item:
                                bonus = item['defense']  # Assuming shields don't have class restrictions
                                c.execute("UPDATE Profile SET def_bonus = def_bonus + ? WHERE user_id = ?",
                                          (bonus, user_id))

                        conn.commit()

                        if item:
                            await update.message.reply_text(f"You equipped <b>{item['name']}</b>.",
                                                            parse_mode='HTML')
                        else:
                            await update.message.reply_text(f"You equipped an item of type {item_type}.")
                else:
                    await update.message.reply_text("This item cannot be equipped.")
            else:
                await update.message.reply_text("Invalid item number or you don't own this item!")

            conn.close()
        else:
            return


async def equipment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """shows equipped weapon and shield"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    if not await user_registered(update):
        await warning_unregistered_user(update, context)
    else:
        if not await user_banned(update):
            user_id = update.effective_message.from_user.id
            equipped_items = c.execute("SELECT * FROM Equipment WHERE user_id = ?", (user_id,)).fetchall()

            if not equipped_items:
                await update.message.reply_text("You have no equipped items.")
                return

            # Get user's class
            playerClass = c.execute("SELECT class FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]

            text = "Your equipped items:\n\n"
            for index, item in enumerate(equipped_items, start=1):
                item_id = item[1]
                item_type = item[2]

                if item_type in weapons:
                    item_info = fetch_weapons(item_type, 0)
                    item_data = next((i for i in item_info if i['id'] == item_id), None)
                    if item_data:
                        item_name = item_data['name']
                        allowed_classes = [c.strip() for c in item_data['classes'].split(',')]
                        bonus = item_data['attack'] if playerClass in allowed_classes else int(item_data['attack'] * 0.4)
                        bonus_text = f"Atk Bonus: +{bonus}"
                        class_text = "" if playerClass in allowed_classes else " (40% efficiency)"
                        text += f"{index}. {item_name} ({item_type}) \n{bonus_text}{class_text}\n"
                elif item_type == 'Shields':
                    item_info = fetch_shields(0)
                    item_data = next((i for i in item_info if i['id'] == item_id), None)
                    if item_data:
                        item_name = item_data['name']
                        bonus_text = f"Def Bonus: +{item_data['defense']}"
                        text += f"{index}. {item_name} ({item_type}) \n{bonus_text}\n"

            text += "\nTo disequip an item, use /unequip <number>"

            await update.message.reply_text(text)

            conn.close()
        else:
            return


async def unequip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """allows users to unequip some equipped items"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    if not await user_registered(update):
        await warning_unregistered_user(update, context)
    else:
        if not await user_banned(update):
            try:
                item_index = int(update.message.text.split(' ', 1)[1]) - 1
            except:
                await update.message.reply_text("Please provide a valid item number.")
                return

            user_id = update.effective_message.from_user.id
            equipped_items = c.execute("SELECT * FROM Equipment WHERE user_id = ?", (user_id,)).fetchall()

            if not equipped_items:
                await update.message.reply_text("You have no equipped items.")
                return

            # Get user's class
            playerClass = c.execute("SELECT class FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]

            if 0 <= item_index < len(equipped_items):
                item_to_remove = equipped_items[item_index]
                item_id = item_to_remove[1]
                item_type = item_to_remove[2]

                c.execute("DELETE FROM Equipment WHERE user_id = ? AND id = ? AND type = ?",
                          (user_id, item_id, item_type))

                # Update bonus in Profile
                if item_type in weapons:
                    item_info = fetch_weapons(item_type, 0)
                    item = next((i for i in item_info if i['id'] == item_id), None)
                    if item:
                        allowed_classes = [c.strip() for c in item['classes'].split(',')]
                        bonus = item['attack'] if playerClass in allowed_classes else int(item['attack'] * 0.4)
                        c.execute("UPDATE Profile SET atk_bonus = atk_bonus - ? WHERE user_id = ?",
                                  (bonus, user_id))
                        await update.message.reply_text(f"You disequipped <b>{item['name']}</b>.", parse_mode='HTML')
                elif item_type == 'Shields':
                    item_info = fetch_shields(0)
                    item = next((i for i in item_info if i['id'] == item_id), None)
                    if item:
                        c.execute("UPDATE Profile SET def_bonus = def_bonus - ? WHERE user_id = ?",
                                  (item['defense'], user_id))
                        await update.message.reply_text(f"You disequipped {item['name']} ({item_type}).")
                else:
                    await update.message.reply_text(f"You disequipped an unknown item.")

                conn.commit()
            else:
                await update.message.reply_text("Invalid item number.")

            conn.close()
        else:
            return


async def start_crafting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """shows the possible potions the user can create"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    user_id = update.effective_user.id
    user_class = c.execute("SELECT class FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]

    # bonus classes
    if user_class not in ['Alchemist', 'Sage']:
        await update.message.reply_text("Only Alchemists and Sages can craft potions.")
        return

    keyboard = [
        [InlineKeyboardButton("Healing Potion", callback_data='craft_1')],
        [InlineKeyboardButton("Brute Force Potion", callback_data='craft_2')],
        [InlineKeyboardButton("Failed Potion", callback_data='craft_3')]
    ]

    # bonus class
    if user_class == 'Sage':
        keyboard.extend([
            [InlineKeyboardButton("Defensive Potion", callback_data='craft_4')],
            [InlineKeyboardButton("Light Feather Potion", callback_data='craft_5')],
            [InlineKeyboardButton("Nectar of Youth", callback_data='craft_6')]
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("With your skills you can choose to create from the following potions:",
                                    reply_markup=reply_markup)
    conn.close()


async def confirm_crafting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage result of the crafting"""
    query = update.callback_query
    await query.answer()

    potion_id = int(query.data.split('_')[2])
    user_id = query.from_user.id

    result = craft_potion(user_id, potion_id)

    if result.startswith("Crafting failed"):
        keyboard = [[InlineKeyboardButton("Back to Potion List", callback_data='back_to_potions')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(result, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await query.edit_message_text(result, parse_mode='HTML')


def check_ingredients(user_id: int, ingredients: list[tuple[str, int]]) -> tuple[bool, list[tuple[str, int, int]]]:
    """checks if user has the needed items to craft selected potion"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    missing_ingredients = []
    has_all = True
    for ingredient_name, required_qt in ingredients:
        ingredient_id = get_item_id(ingredient_name)
        if ingredient_id:
            user_qt = c.execute("SELECT qt FROM Inventory WHERE user_id = ? AND id = ? AND type = 'Item'", (user_id, ingredient_id)).fetchone()
            if not user_qt or user_qt[0] < required_qt:
                has_all = False
                missing_ingredients.append((ingredient_name, required_qt, user_qt[0] if user_qt else 0))
        else:
            has_all = False
            missing_ingredients.append((ingredient_name, required_qt, 0))
    conn.close()
    return has_all, missing_ingredients


def craft_potion(user_id: int, potion_id: int) -> str:
    """adds the selected potion to user inventory if requirements applied"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    potion_name, potion_rarity, potion_type, potion_bonus, ingredients = get_potion_info(potion_id)

    # Check ingredients again before crafting
    has_ingredients, missing_ingredients = check_ingredients(user_id, ingredients)
    if not has_ingredients:
        conn.close()
        missing_text = "\n".join([f"- <b>{name}</b> (Need: {need}, Have: {have})" for name, need, have in missing_ingredients])
        return f"Crafting failed. You don't have all the necessary ingredients:\n\n{missing_text}"

    # Remove ingredients from inventory
    for ingredient_name, required_qt in ingredients:
        ingredient_id = get_item_id(ingredient_name)
        c.execute("UPDATE Inventory SET qt = qt - ? WHERE user_id = ? AND id = ? AND type = 'Item'",
                  (required_qt, user_id, ingredient_id))
        c.execute("DELETE FROM Inventory WHERE user_id = ? AND id = ? AND type = 'Item' AND qt <= 0",
                  (user_id, ingredient_id))

    # Add potion to inventory
    existing_potion = c.execute("SELECT qt FROM Inventory WHERE user_id = ? AND id = ? AND type = ?",
                                (user_id, potion_id, potion_type)).fetchone()
    if existing_potion:
        c.execute("UPDATE Inventory SET qt = qt + 1 WHERE user_id = ? AND id = ? AND type = ?",
                  (user_id, potion_id, potion_type))
    else:
        c.execute("INSERT INTO Inventory (user_id, id, name, rarity, type, qt) VALUES (?, ?, ?, ?, ?, 1)",
                  (user_id, potion_id, potion_name, potion_rarity, potion_type))

    conn.commit()
    conn.close()

    return f"You have successfully crafted: <b>{potion_name}</b> <i>(+{potion_bonus} {potion_type.split('Potion')[1]})</i>"


async def potion_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage buttons of start_crafting function"""
    query = update.callback_query
    await query.answer()

    potion_id = int(query.data.split('_')[1])
    user_id = query.from_user.id

    potion_name, potion_rarity, potion_type, potion_bonus, ingredients = get_potion_info(potion_id)

    info_text = f"<b>{potion_name}</b>\n\n"
    info_text += f"<b>Rarity:</b> <i>{potion_rarity}</i>\n"
    info_text += f"<b>Effect:</b> <i>+{potion_bonus} {potion_type.split('Potion')[1]}</i>\n\n"
    info_text += "<b>Ingredients:</b>\n"
    for ing_name, ing_qty in ingredients:
        info_text += f"- <b>{ing_name}:</b> <i>{ing_qty}</i>\n"

    has_ingredients, missing_ingredients = check_ingredients(user_id, ingredients)

    keyboard = [
        [InlineKeyboardButton("Craft Potion", callback_data=f'confirm_craft_{potion_id}')],
        [InlineKeyboardButton("Back to Potion List", callback_data='back_to_potions')]
    ]

    if has_ingredients:
        info_text += "\nYou have all the necessary ingredients. Do you want to proceed with crafting?"
    else:
        info_text += "\nYou don't have all the necessary ingredients.\nMissing:\n"
        info_text += "\n".join([f"- <b>{name}</b> (Need: {need}, Have: {have})" for name, need, have in missing_ingredients])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(info_text, reply_markup=reply_markup, parse_mode='HTML')


async def back_to_potions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """shows main menu of craft potions"""
    query = update.callback_query
    await query.answer()

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    user_id = query.from_user.id
    user_class = c.execute("SELECT class FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]

    keyboard = [
        [InlineKeyboardButton("Healing Potion", callback_data='craft_1')],
        [InlineKeyboardButton("Brute Force Potion", callback_data='craft_2')],
        [InlineKeyboardButton("Failed Potion", callback_data='craft_3')]
    ]

    if user_class == 'Sage':
        keyboard.extend([
            [InlineKeyboardButton("Defensive Potion", callback_data='craft_4')],
            [InlineKeyboardButton("Light Feather Potion", callback_data='craft_5')],
            [InlineKeyboardButton("Nectar of Youth", callback_data='craft_6')]
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("With your skills you can choose to create from the following potions:",
                                  reply_markup=reply_markup)
    conn.close()


async def use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """allows users to use some items, based on category"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    if not await user_registered(update):
        await warning_unregistered_user(update, context)
        return

    if await user_banned(update):
        return

    if await user_is_trading(update):
        await warning_trading_user(update, context)
        return

    try:
        item_index = int(update.message.text.split(' ', 2)[1]) - 1
    except:
        await update.message.reply_text("Please provide a valid item number.")
        conn.close()
        return

    try:
        qt = int(update.effective_message.text.split(' ', 2)[2])
    except:
        qt = 1

    if qt <= 0:
        await update.message.reply_text("Quantity must be greater than zero.")
        conn.close()
        return

    user_id = update.effective_user.id
    items = c.execute("SELECT * FROM Inventory WHERE user_id = ?", (user_id,)).fetchall()

    if 0 <= item_index < len(items):
        item = items[item_index]
        itemID = item[1]
        itemType = item[4]
        item_quantity = item[5]

        if item_quantity >= qt:
            if itemType.startswith("Potion"):
                itemName, itemRarity, itemPrice, _ = get_potion(itemID)
            else:
                itemName, itemRarity, itemPrice, _ = inspect_item(itemID)

            if "Heal" in itemType:
                await use_heal_item(update, c, user_id, itemName, itemRarity, qt)
            elif "Mystery" in itemType:
                await use_mystery_item(update, c, user_id, itemName, itemRarity, qt)
            elif itemType.startswith("Potion"):
                await use_potion(update, c, user_id, itemName, itemType, qt)
            else:
                await update.message.reply_text("This type of item cannot be used.")
                conn.close()
                return

            # Remove used items from inventory
            new_quantity = item_quantity - qt

            if new_quantity > 0:
                c.execute("UPDATE Inventory SET qt = ? WHERE user_id = ? AND id = ? AND type = ?",
                          (new_quantity, user_id, itemID, itemType))
            else:
                c.execute("DELETE FROM Inventory WHERE user_id = ? AND id = ? AND type = ?",
                          (user_id, itemID, itemType))

            conn.commit()
        else:
            await update.message.reply_text("You don't have this item in sufficient quantity!")
    else:
        await update.message.reply_text("Invalid item number or you don't own this item!")

    conn.close()


async def use_potion(update: Update, c, user_id, itemName, itemType, qt):
    """consume potion and gives rewards based on category of it"""
    potion_effect = itemType.split('Potion')[1]

    try:
        bonus = get_potion_bonus(itemName)
    except ValueError as e:
        await update.message.reply_text(f"Error: {str(e)}")
        return

    total_bonus = bonus * qt
    current_hp, max_hp = c.execute("SELECT hp, hp_max FROM Profile WHERE user_id = ?", (user_id,)).fetchone()

    if potion_effect == "HP":
        new_hp = min(current_hp + total_bonus, max_hp)
        healed = new_hp - current_hp
        c.execute("UPDATE Profile SET hp = MIN(hp + ?, hp_max) WHERE user_id = ?", (total_bonus, user_id))
        await update.message.reply_text(f"You used <i>{qt} {itemName}(s)</i> and restored <b>{healed} HP</b>!",
                                        parse_mode='HTML')
    elif potion_effect == "Atk":
        c.execute("UPDATE Profile SET atk = atk + ? WHERE user_id = ?", (total_bonus, user_id))
        await update.message.reply_text(f"You used <i>{qt} {itemName}(s)</i> and increased your ATK by <b>{total_bonus}</b>!",
                                        parse_mode='HTML')
    elif potion_effect == "Def":
        c.execute("UPDATE Profile SET def = def + ? WHERE user_id = ?", (total_bonus, user_id))
        await update.message.reply_text(f"You used <i>{qt} {itemName}(s)</i> and increased your DEF by <b>{total_bonus}</b>!",
                                        parse_mode='HTML')
    elif potion_effect == "Vel":
        c.execute("UPDATE Profile SET vel = vel + ? WHERE user_id = ?", (total_bonus, user_id))
        await update.message.reply_text(f"You used <i>{qt} {itemName}(s)</i> and increased your VEL by <b>{total_bonus}!</b>",
                                        parse_mode='HTML')
    elif potion_effect == "HPMax":
        c.execute("UPDATE Profile SET hp_max = hp_max + ?, hp = hp + ? WHERE user_id = ?", (total_bonus, total_bonus, user_id))
        await update.message.reply_text(f"You used <i>{qt} {itemName}(s)</i> and increased your max HP by <b>{total_bonus}</b>!",
                                        parse_mode='HTML')
    elif potion_effect == "Exp":
        c.execute("UPDATE Profile SET exp = exp + ? WHERE user_id = ?", (total_bonus, user_id))
        await update.message.reply_text(f"You used <i>{qt} {itemName}(s)</i> and gained <b>{total_bonus} Exp</b>!",
                                        parse_mode='HTML')
    else:
        await update.message.reply_text("Unknown potion effect.")


async def use_heal_item(update, u, user_id, itemName, itemRarity, qt):
    """allows users to heal x HP based on rarity of the item"""
    total_heal = sum(calculate_heal_amount(itemRarity) for _ in range(qt))

    current_hp, max_hp = u.execute("SELECT hp, hp_max FROM Profile WHERE user_id = ?", (user_id,)).fetchone()

    new_hp = min(current_hp + total_heal, max_hp)
    healed = new_hp - current_hp

    u.execute("UPDATE Profile SET hp = ? WHERE user_id = ?", (new_hp, user_id))

    await update.message.reply_text(f"You used <i>{qt} {itemName}</i> and recovered <b>{healed} HP</b>.", parse_mode='HTML')


async def use_mystery_item(update, c, user_id, itemName, itemRarity, qt):
    """allows users to earn rewards based on rarity of item"""
    total_exp = 0
    total_gold = 0

    user_class = c.execute("SELECT class FROM Profile WHERE user_id = ?", (user_id,)).fetchone()[0]

    for _ in range(qt):
        reward_type, reward_amount = generate_mystery_reward(itemRarity, user_class)
        if reward_type == 'exp':
            total_exp += reward_amount
        elif reward_type == 'gold':
            total_gold += reward_amount

    if total_exp > 0:
        c.execute("UPDATE User SET exp = exp + ? WHERE user_id = ?", (total_exp, user_id))
    if total_gold > 0:
        c.execute("UPDATE User SET gold = gold + ? WHERE user_id = ?", (total_gold, user_id))

    reward_message = f"You opened <i>{qt} {itemName}</i> and obtained:\n\n"
    if total_exp > 0:
        reward_message += f"- <b>{total_exp} exp</b>\n"
    if total_gold > 0:
        reward_message += f"- <b>{total_gold} gold</b>\n"
    if total_exp == 0 and total_gold == 0:
        reward_message += "Nothing"

    await update.message.reply_text(reward_message, parse_mode='HTML')