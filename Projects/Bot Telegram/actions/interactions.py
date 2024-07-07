import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.helpers import check_chat

TRADE_TIMEOUT = 300  # 5 minutes timeout for each trade stage
ITEMS_PER_PAGE = 5 # Number of items to show per page

def remove_existing_trade_jobs(context: ContextTypes.DEFAULT_TYPE, trade_id: int) -> bool:
    """Remove trade jobs for the given trade_id. Returns whether any job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(f'trade_{trade_id}')
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

def update_trade_timer(context: ContextTypes.DEFAULT_TYPE, trade_id: int, chat_id: int,
                       message_id: int = None, private_messages: dict = None, summary_messages: dict = None):
    """manage the jobs related to the trades"""
    remove_existing_trade_jobs(context, trade_id)
    job_data = {
        'trade_id': trade_id,
        'chat_id': chat_id,
        'message_id': message_id,
    }
    if private_messages:
        job_data['private_messages'] = private_messages
    if summary_messages:
        job_data['summary_messages'] = summary_messages

    context.job_queue.run_once(
        check_trade_timeout,
        TRADE_TIMEOUT,
        name=f'trade_{trade_id}',
        data=job_data
    )

def get_user_nickname(c, user_id):
    result = c.execute("SELECT nickname FROM User WHERE user_id = ?", (user_id,)).fetchone()
    return result[0] if result else f"User {user_id}"

async def start_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """beginning of the trade"""
    user = update.effective_user
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    if not can_start_trade(c, user.id):
        await update.message.reply_text("You can't start a trade at the moment.")
        conn.close()
        return

    if await check_chat(update):
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT INTO Exchange (initiator_id, status, timestamp) VALUES (?, 'waiting_join', ?)",
                  (user.id, current_time,))
        trade_id = c.lastrowid
        c.execute("UPDATE Profile SET status = 'trading' WHERE user_id = ?", (user.id,))
        conn.commit()

        nickname = get_user_nickname(c, user.id)
        keyboard = [[InlineKeyboardButton("Join Trade", callback_data=f"join_trade_{trade_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = await update.message.reply_text(
            f"Trade started by {nickname} (ID: {trade_id})",
            reply_markup=reply_markup
        )

        update_trade_timer(context, trade_id, update.effective_chat.id, message.message_id)

        conn.close()
    else:
        await update.message.reply_text("You can't start a trade in a private chat!")

async def join_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """allow users to join a trade if possible"""
    query = update.callback_query
    user = query.from_user
    trade_id = int(query.data.split('_')[2])

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    if not can_join_trade(c, user.id, trade_id):
        await query.answer("You can't join this trade.")
        conn.close()
        return

    trade_info = c.execute("SELECT initiator_id FROM Exchange WHERE id = ?", (trade_id,)).fetchone()
    initiator_id = trade_info[0]

    initiator_nickname = get_user_nickname(c, initiator_id)
    joiner_nickname = get_user_nickname(c, user.id)

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE Exchange SET joiner_id = ?, status = 'waiting_confirm', timestamp = ? WHERE id = ?",
              (user.id, current_time, trade_id,))
    c.execute("UPDATE Profile SET status = 'trading' WHERE user_id = ?", (user.id,))
    conn.commit()

    keyboard = [
        [InlineKeyboardButton("Continue", callback_data=f"continue_trade_{trade_id}")],
        [InlineKeyboardButton("Cancel", callback_data=f"cancel_trade_{trade_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"Trade (ID: {trade_id}) between <b>{initiator_nickname}</b> and <b>{joiner_nickname}</b>\n"
        f"Waiting for <b>{initiator_nickname}</b> to continue the trade.",
        reply_markup=reply_markup, parse_mode='HTML'
    )

    update_trade_timer(context, trade_id, update.effective_chat.id, query.message.message_id)

    conn.close()

async def continue_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """allows users to continue the trade"""
    query = update.callback_query
    trade_id = int(query.data.split('_')[2])

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    trade_info = c.execute("SELECT initiator_id, joiner_id FROM Exchange WHERE id = ?", (trade_id,)).fetchone()
    if not trade_info:
        await query.answer("Trade not found.")
        conn.close()
        return

    initiator_id, joiner_id = trade_info

    if query.from_user.id != initiator_id:
        await query.answer("Only the trade initiator can continue the trade.")
        conn.close()
        return

    private_messages = {}
    for user_id in (initiator_id, joiner_id):
        message = await context.bot.send_message(
            chat_id=user_id,
            text="Select items and gold to trade:",
            reply_markup=get_trade_options_keyboard(trade_id)
        )
        private_messages[user_id] = message.message_id

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE Exchange SET status = 'selecting_items', timestamp = ? WHERE id = ?", (current_time, trade_id,))
    conn.commit()

    await query.edit_message_text("The trade continues in the participants' private chats.")

    update_trade_timer(context, trade_id, update.effective_chat.id, query.message.message_id, private_messages=private_messages)

    conn.close()

def get_trade_options_keyboard(trade_id):
    keyboard = [
        [InlineKeyboardButton("Add Item", callback_data=f"add_item_{trade_id}")],
        [InlineKeyboardButton("Add Gold", callback_data=f"add_gold_{trade_id}")],
        [InlineKeyboardButton("Confirm Offer", callback_data=f"confirm_offer_{trade_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def add_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """adds buttons basing on the inventory of the user allowing to choose one among them"""
    query = update.callback_query
    data = query.data.split('_')
    trade_id = int(data[2])
    page = int(data[3]) if len(data) > 3 else 0
    user_id = query.from_user.id

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE Exchange SET timestamp = ? WHERE id = ?", (current_time, trade_id))

    inventory = c.execute("""
        SELECT i.id, i.name, i.qt, i.type, COALESCE(e.id, 0) as equipped
        FROM Inventory i
        LEFT JOIN Equipment e ON i.user_id = e.user_id AND i.id = e.id AND i.type = e.type
        WHERE i.user_id = ? AND i.qt > 0
    """, (user_id,)).fetchall()

    if not inventory:
        await query.answer("You don't have any items to trade.")
        conn.close()
        return

    total_pages = (len(inventory) - 1) // ITEMS_PER_PAGE + 1
    start_index = page * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    current_page_items = inventory[start_index:end_index]

    keyboard = []
    for item in current_page_items:
        item_id, name, quantity, item_type, is_equipped = item
        available_quantity = quantity - 1 if is_equipped else quantity
        if available_quantity > 0:
            keyboard.append([InlineKeyboardButton(
                f"{name} (x{available_quantity})",
                callback_data=f"select_item_{trade_id}_{item_type}_{item_id}"
            )])

    # Add navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"add_item_{trade_id}_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"add_item_{trade_id}_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("Back to menu", callback_data=f"back_to_trade_{trade_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(f"Select an item to add to the trade\n"
                                  f"<i>(Page {page+1}/{total_pages})</i>:", reply_markup=reply_markup, parse_mode='HTML')

    update_trade_timer(context, trade_id, update.callback_query.message.chat.id, query.message.message_id)

    conn.close()


async def select_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage buttons of add items"""
    query = update.callback_query
    trade_id, item_type, item_id = query.data.split('_')[2:]
    item_id = int(item_id)
    user_id = query.from_user.id

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE Exchange SET timestamp = ? WHERE id = ?", (current_time, trade_id))

    item_info = c.execute("""
        SELECT i.name, i.qt, COALESCE(e.id, 0) as equipped
        FROM Inventory i
        LEFT JOIN Equipment e ON i.user_id = e.user_id AND i.id = e.id AND i.type = e.type
        WHERE i.user_id = ? AND i.id = ? AND i.type = ?
    """, (user_id, item_id, item_type)).fetchone()

    if not item_info:
        await query.answer("Item not found in your inventory.")
        conn.close()
        return

    name, quantity, is_equipped = item_info
    available_quantity = quantity - 1 if is_equipped else quantity

    # Check if the item is already in the trade
    existing_quantity = c.execute(
        "SELECT quantity FROM TradeDetails WHERE trade_id = ? AND user_id = ? AND item_id = ? AND item_type = ?",
        (trade_id, user_id, item_id, item_type)).fetchone()

    if existing_quantity:
        existing_quantity = existing_quantity[0]
        if existing_quantity >= available_quantity:
            await query.answer(f"You've already added all available {name} to the trade.")
            conn.close()
            return
        max_additional = available_quantity - existing_quantity
        await query.edit_message_text(
            f"You've already added <i>{existing_quantity} {name}</i>. How many more do you want to add? "
            f"<i>(1-{max_additional})</i>", parse_mode='HTML'
        )
        context.user_data['awaiting_item_quantity'] = (trade_id, item_type, item_id, max_additional, existing_quantity)
    else:
        await query.edit_message_text(f"How many <i>{name}</i> do you want to add? <i>(1-{available_quantity})</i>",
                                      parse_mode='HTML')
        context.user_data['awaiting_item_quantity'] = (trade_id, item_type, item_id, available_quantity, 0)

    update_trade_timer(context, trade_id, update.callback_query.message.chat.id, query.message.message_id)

    conn.close()


async def handle_item_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """save the written quantity of the selected item"""
    if 'awaiting_item_quantity' not in context.user_data:
        return

    trade_id, item_type, item_id, max_quantity, existing_quantity = context.user_data['awaiting_item_quantity']
    user_id = update.effective_user.id
    try:
        quantity = int(update.message.text)
        if quantity <= 0 or quantity > max_quantity:
            raise ValueError
    except ValueError:
        await update.message.reply_text(f"Please enter a valid number between <b>1</b> and <b>{max_quantity}</b>.",
                                        parse_mode='HTML')
        return

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    new_quantity = existing_quantity + quantity

    if existing_quantity > 0:
        c.execute("""
            UPDATE TradeDetails 
            SET quantity = ? 
            WHERE trade_id = ? AND user_id = ? AND item_id = ? AND item_type = ?
        """, (new_quantity, trade_id, user_id, item_id, item_type))
    else:
        c.execute("""
            INSERT INTO TradeDetails (trade_id, user_id, item_id, item_type, quantity) 
            VALUES (?, ?, ?, ?, ?)
        """, (trade_id, user_id, item_id, item_type, quantity))

    conn.commit()

    item_name = c.execute("SELECT name FROM Inventory WHERE id = ? AND type = ? AND user_id = ?",
                          (item_id, item_type, user_id)).fetchone()[0]
    await update.message.reply_text(
        f"<i>{item_name}</i> added to trade. Total in trade: <b>{new_quantity}</b>.",
        reply_markup=get_trade_options_keyboard(trade_id), parse_mode='HTML')

    del context.user_data['awaiting_item_quantity']

    conn.close()

async def add_gold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """asks input of golds basing on the gold of the user"""
    query = update.callback_query
    trade_id = int(query.data.split('_')[2])
    user_id = query.from_user.id

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    user_gold = c.execute("SELECT gold FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE Exchange SET timestamp = ? WHERE id = ?", (current_time, trade_id))

    if user_gold <= 0:
        await query.answer("You don't have any gold to trade.")
        conn.close()
        return

    current_gold = c.execute("SELECT gold FROM TradeDetails WHERE trade_id = ? AND user_id = ?",
                             (trade_id, user_id)).fetchone()
    current_amount = current_gold[0] if current_gold else 0

    await query.edit_message_text(f"You have <b>{user_gold} gold</b>. Current trade amount: <b>{current_amount}</b>.\n"
                                  f"Enter the new amount you want to add to the trade:", parse_mode='HTML')

    context.user_data['awaiting_gold_amount'] = (trade_id, user_id)
    update_trade_timer(context, trade_id, update.callback_query.message.chat.id, query.message.message_id)

    conn.close()


async def handle_gold_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """manage input text from the user and save it when it is acceptable"""
    if 'awaiting_gold_amount' not in context.user_data:
        return

    trade_id, user_id = context.user_data['awaiting_gold_amount']

    try:
        amount = int(update.message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid positive number greater than <b>0</b>.", parse_mode='HTML')
        return

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    user_gold = c.execute("SELECT gold FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]

    if amount > user_gold:
        await update.message.reply_text(f"You don't have enough gold. Your balance is <b>{user_gold}</b>.", parse_mode='HTML')
        conn.close()
        return

    existing_record = c.execute("SELECT gold FROM TradeDetails WHERE trade_id = ? AND user_id = ?",
                                (trade_id, user_id)).fetchone()

    if existing_record:
        c.execute("UPDATE TradeDetails SET gold = ? WHERE trade_id = ? AND user_id = ?",
                  (amount, trade_id, user_id))
    else:
        c.execute("INSERT INTO TradeDetails (trade_id, user_id, gold) VALUES (?, ?, ?)",
                  (trade_id, user_id, amount))

    conn.commit()

    updated_gold = c.execute("SELECT gold FROM TradeDetails WHERE trade_id = ? AND user_id = ?",
                             (trade_id, user_id)).fetchone()[0]

    await update.message.reply_text(f"Gold updated. Total gold in trade: <b>{updated_gold}</b>.",
                                    reply_markup=get_trade_options_keyboard(trade_id), parse_mode='HTML')

    del context.user_data['awaiting_gold_amount']
    conn.close()


async def back_to_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """allows user to go back to the main menu of the ongoing trade"""
    query = update.callback_query
    trade_id = int(query.data.split('_')[3])

    await query.edit_message_text("Select items and gold to trade:",
                                  reply_markup=get_trade_options_keyboard(trade_id))

async def confirm_offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """confirmation of the offer after putting inside at least an item or some gold"""
    query = update.callback_query
    trade_id = int(query.data.split('_')[2])
    user_id = query.from_user.id

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    trade_details = c.execute("""
        SELECT COUNT(*) FROM TradeDetails 
        WHERE trade_id = ? AND user_id = ? AND (item_id IS NOT NULL OR gold IS NOT NULL)
    """, (trade_id, user_id)).fetchone()

    if trade_details[0] == 0:
        await query.answer(text="You can't confirm an empty offer. Please add items or gold to the trade.", show_alert=True)
        conn.close()
        return

    c.execute("SELECT initiator_id, joiner_id, initiator_status, joiner_status FROM Exchange WHERE id = ?", (trade_id,))
    trade_info = c.fetchone()

    if not trade_info:
        await query.answer("This trade no longer exists.")
        conn.close()
        return

    initiator_id, joiner_id, initiator_status, joiner_status = trade_info

    if user_id not in (initiator_id, joiner_id):
        await query.answer("You are not part of this trade.")
        conn.close()
        return

    status_column = 'initiator_status' if user_id == initiator_id else 'joiner_status'
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    c.execute(f"UPDATE Exchange SET {status_column} = ?, timestamp = ? WHERE id = ?",
              ('confirmed', current_time, trade_id))
    conn.commit()

    await query.answer("Your offer has been confirmed.")

    if (initiator_status == 'confirmed' and user_id == joiner_id) or (
                joiner_status == 'confirmed' and user_id == initiator_id):
        # Both users have accepted, finalize the trade
        await show_final_summary(update, context, trade_id)
    else:
        # This is the first user to accept
        await query.edit_message_text(
            "Your offer has been confirmed. Waiting for the other participant to confirm their offer."
            )

    conn.close()

async def show_final_summary(update, context, trade_id):
    """sends summary of the trade to the users related to the ongoing trade"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()
    query = update.callback_query

    trade_details = c.execute(
        "SELECT initiator_id, joiner_id FROM Exchange WHERE id = ?",
        (trade_id,)).fetchone()

    summary = f"Trade (ID: {trade_id}) Summary:\n\n"

    for user_id in trade_details:
        nickname = get_user_nickname(c, user_id)
        summary += f"Offer from <b>{nickname}</b>:\n"
        items = c.execute("""
            SELECT td.item_id, td.item_type, td.quantity, i.name
            FROM TradeDetails td
            JOIN Inventory i ON td.user_id = i.user_id AND td.item_id = i.id AND td.item_type = i.type
            WHERE td.trade_id = ? AND td.user_id = ? AND td.item_id IS NOT NULL
        """, (trade_id, user_id)).fetchall()
        for item in items:
            summary += f"- {item[3]} ({item[1]}): x{item[2]}\n"

        gold = c.execute("SELECT gold FROM TradeDetails WHERE trade_id = ? AND user_id = ? AND gold IS NOT NULL",
                          (trade_id, user_id)).fetchone()
        if gold:
            summary += f"Gold: <b>{gold[0]}</b>\n"
        summary += "\n"

    keyboard = [
        [InlineKeyboardButton("Accept", callback_data=f"accept_trade_{trade_id}")],
        [InlineKeyboardButton("Decline", callback_data=f"decline_trade_{trade_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    summary_messages = {}
    for user_id in trade_details:
        message = await context.bot.send_message(
            chat_id=user_id,
            text=summary,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        summary_messages[user_id] = message.message_id

    if query and query.message:
        await query.message.delete()

    update_trade_timer(context, trade_id, update.effective_chat.id, summary_messages=summary_messages)

    conn.close()

async def accept_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """allows users to accept the trade after seeing the summary"""
    query = update.callback_query
    trade_id = int(query.data.split('_')[2])
    user_id = query.from_user.id

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    c.execute("SELECT initiator_id, joiner_id, initiator_status, joiner_status FROM Exchange WHERE id = ?", (trade_id,))
    initiator_id, joiner_id, initiator_status, joiner_status = c.fetchone()

    status_column = 'initiator_status' if user_id == initiator_id else 'joiner_status'
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    c.execute(f"UPDATE Exchange SET {status_column} = ?, timestamp = ? WHERE id = ?",
              ('accepted', current_time, trade_id))
    conn.commit()

    if (initiator_status == 'accepted' and user_id == joiner_id) or (
            joiner_status == 'accepted' and user_id == initiator_id):
        # Both users have accepted, finalize the trade
        await finalize_trade(update, context, trade_id, query)
    else:
        # This is the first user to accept
        await query.edit_message_text("You have accepted the trade. Waiting for the other participant's acceptance.")
        other_user_id = joiner_id if user_id == initiator_id else initiator_id

        await context.bot.send_message(
            chat_id=other_user_id,
            text="The other participant has accepted the trade. You can still choose to accept or decline."
        )

    conn.close()


async def decline_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """allows users to decline the trade after seeing the summary"""
    query = update.callback_query
    trade_id = int(query.data.split('_')[2])

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    trade_info = c.execute("SELECT initiator_id, joiner_id FROM Exchange WHERE id = ?", (trade_id,)).fetchone()

    if not trade_info:
        await query.answer("This trade no longer exists.")
        conn.close()
        return

    initiator_id, joiner_id = trade_info

    c.execute("DELETE FROM Exchange WHERE id = ?", (trade_id,))
    c.execute("DELETE FROM TradeDetails WHERE trade_id = ?", (trade_id,))
    c.execute("UPDATE Profile SET status = 'idle' WHERE user_id IN (?, ?)", (initiator_id, joiner_id))
    conn.commit()

    decline_message = f"Trade (ID: {trade_id}) has been declined and cancelled."

    last_job = context.job_queue.get_jobs_by_name(f'trade_{trade_id}')[-1]
    summary_messages = last_job.data.get('summary_messages', {})

    for uid, message_id in summary_messages.items():
        try:
            await context.bot.edit_message_text(
                chat_id=uid,
                message_id=message_id,
                text=decline_message
            )
        except Exception as e:
            print(f"Failed to edit summary message for user {uid}: {e}")
            try:
                await context.bot.send_message(chat_id=uid, text=decline_message)
            except Exception as e:
                print(f"Failed to send decline message to user {uid}: {e}")

    remove_existing_trade_jobs(context, trade_id)

    conn.close()

    await query.answer("Trade declined successfully.")

async def finalize_trade(update, context, trade_id, query=None):
    """once both users accept the trade, the latter will be applied by moving the items and gold to the new owners"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    trade_details = c.execute(
        "SELECT initiator_id, joiner_id FROM Exchange WHERE id = ?",
        (trade_id,)).fetchone()

    # Transfer items and gold
    for from_user_id in trade_details:
        to_user_id = trade_details[1] if from_user_id == trade_details[0] else trade_details[0]

        # Transfer items
        items = c.execute("""
            SELECT item_id, item_type, quantity 
            FROM TradeDetails 
            WHERE trade_id = ? AND user_id = ? AND item_id IS NOT NULL
        """, (trade_id, from_user_id)).fetchall()
        for item_id, item_type, quantity in items:
            # Get item info before removing
            item_info = c.execute("""
                SELECT name, rarity, type 
                FROM Inventory 
                WHERE user_id = ? AND id = ? AND type = ?
            """, (from_user_id, item_id, item_type)).fetchone()

            # Remove items from sender
            c.execute("""
                UPDATE Inventory 
                SET qt = qt - ? 
                WHERE user_id = ? AND id = ? AND type = ?
            """, (quantity, from_user_id, item_id, item_type))

            # If quantity becomes 0, remove the item from inventory
            c.execute("""
                DELETE FROM Inventory 
                WHERE user_id = ? AND id = ? AND type = ? AND qt <= 0
            """, (from_user_id, item_id, item_type))

            # Add items to receiver
            existing = c.execute("""
                SELECT qt 
                FROM Inventory 
                WHERE user_id = ? AND id = ? AND type = ?
            """, (to_user_id, item_id, item_type)).fetchone()
            if existing:
                c.execute("""
                    UPDATE Inventory 
                    SET qt = qt + ? 
                    WHERE user_id = ? AND id = ? AND type = ?
                """, (quantity, to_user_id, item_id, item_type))
            else:
                if item_info:
                    c.execute("""
                        INSERT INTO Inventory (user_id, id, name, rarity, type, qt) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (to_user_id, item_id, item_info[0], item_info[1], item_info[2], quantity))
                else:
                    print(f"Warning: Item info not found for item_id {item_id} and type {item_type}")

        # Transfer gold
        gold = c.execute("SELECT gold FROM TradeDetails WHERE trade_id = ? AND user_id = ? AND gold IS NOT NULL",
                          (trade_id, from_user_id)).fetchone()
        if gold:
            amount = gold[0]
            c.execute("UPDATE User SET gold = gold - ? WHERE user_id = ?", (amount, from_user_id))
            c.execute("UPDATE User SET gold = gold + ? WHERE user_id = ?", (amount, to_user_id))

    # Set users' status back to 'idle'
    for user_id in trade_details:
        c.execute("UPDATE Profile SET status = 'idle' WHERE user_id = ?", (user_id,))

    # Delete trade records
    c.execute("DELETE FROM Exchange WHERE id = ?", (trade_id,))
    c.execute("DELETE FROM TradeDetails WHERE trade_id = ?", (trade_id,))
    conn.commit()

    success_message = f"Trade (ID: {trade_id}) has been successfully completed!"

    last_job = context.job_queue.get_jobs_by_name(f'trade_{trade_id}')[-1]
    summary_messages = last_job.data.get('summary_messages', {})

    for user_id in trade_details:
        try:
            if user_id in summary_messages:
                await context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=summary_messages[user_id],
                    text=success_message
                )
            else:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=success_message
                )
        except Exception as e:
            print(f"Failed to send/edit message to user {user_id}: {e}")

    remove_existing_trade_jobs(context, trade_id)

    conn.close()

async def cancel_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """deleting the trade"""
    query = update.callback_query
    trade_id = int(query.data.split('_')[2])
    user_id = query.from_user.id

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    trade_info = c.execute("SELECT initiator_id, joiner_id FROM Exchange WHERE id = ?", (trade_id,)).fetchone()

    if trade_info and (user_id == trade_info[0] or user_id == trade_info[1]):
        c.execute("DELETE FROM Exchange WHERE id = ?", (trade_id,))
        c.execute("DELETE FROM TradeDetails WHERE trade_id = ?", (trade_id,))
        c.execute("UPDATE Profile SET status = 'idle' WHERE user_id IN (?, ?)", (trade_info[0], trade_info[1]))
        conn.commit()

        await query.edit_message_text("Trade cancelled.")

        other_user_id = trade_info[1] if user_id == trade_info[0] else trade_info[0]
        if other_user_id:
            try:
                await context.bot.send_message(chat_id=other_user_id,
                                               text=f"The trade (ID: {trade_id}) has been cancelled by the other participant.")
            except Exception as e:
                print(f"Failed to notify user {other_user_id}: {e}")

        remove_existing_trade_jobs(context, trade_id)
    else:
        await query.answer("You are not authorized to cancel this trade.")

    conn.close()

async def check_trade_timeout(context: ContextTypes.DEFAULT_TYPE) -> None:
    """check if the timer is done, if positive the trade will be deleted"""
    job = context.job
    trade_id = job.data['trade_id']
    chat_id = job.data['chat_id']
    message_id = job.data.get('message_id')
    private_messages = job.data.get('private_messages', {})
    summary_messages = job.data.get('summary_messages', {})

    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    trade_info = c.execute("SELECT status, timestamp, initiator_id, joiner_id FROM Exchange WHERE id = ?", (trade_id,)).fetchone()

    if not trade_info:
        conn.close()
        return

    status, timestamp, initiator_id, joiner_id = trade_info
    current_time = datetime.now()
    time_difference = current_time - datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')

    if time_difference.total_seconds() > TRADE_TIMEOUT:
        c.execute("DELETE FROM Exchange WHERE id = ?", (trade_id,))
        c.execute("DELETE FROM TradeDetails WHERE trade_id = ?", (trade_id,))
        c.execute("UPDATE Profile SET status = 'idle' WHERE user_id IN (?, ?)", (initiator_id, joiner_id))
        conn.commit()

        timeout_message = f"Trade {trade_id} has been cancelled due to inactivity."

        for user_id in {initiator_id, joiner_id}:
            try:
                if user_id in private_messages:
                    await context.bot.delete_message(chat_id=user_id, message_id=private_messages[user_id])
                if user_id in summary_messages:
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=summary_messages[user_id],
                        text=timeout_message
                    )
                else:
                    await context.bot.send_message(chat_id=user_id, text=timeout_message)
            except Exception as e:
                print(f"Failed to handle timeout for user {user_id}: {e}")

        if message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=timeout_message
                )
            except Exception:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=timeout_message)
                except Exception as e:
                    print(f"Failed to send timeout message to chat {chat_id}: {e}")

    conn.close()

# Helper functions
def can_start_trade(cursor, user_id):
    user = cursor.execute("SELECT status FROM Profile WHERE user_id = ?", (user_id,)).fetchone()
    return user and user[0] == 'idle'

def can_join_trade(cursor, user_id, trade_id):
    trade = cursor.execute("SELECT * FROM Exchange WHERE id = ? AND status = 'waiting_join'", (trade_id,)).fetchone()
    if not trade or trade[1] == user_id:
        return False

    user = cursor.execute("SELECT status FROM Profile WHERE user_id = ?", (user_id,)).fetchone()
    return user and user[0] == 'idle'

def is_item_equipped(cursor, user_id, item_id):
    equipped = cursor.execute("SELECT * FROM Equipment WHERE user_id = ? AND id = ?", (user_id, item_id)).fetchone()
    return equipped is not None