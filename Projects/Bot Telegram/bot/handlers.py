import re
import sqlite3
from telegram import Update
from telegram.ext import CommandHandler, ConversationHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

from admin.commands import restorationGuild, players, addGold, addLvl, ban, unban, announce
from actions.combat import battle, continue_battle, flee_battle
from actions.exploration import travel, travel_cb, explore
from actions.interactions import (start_trade, join_trade, continue_trade, cancel_trade,
                                  add_item, select_item, handle_item_quantity,
                                  add_gold, handle_gold_amount,
                                  back_to_trade, confirm_offer, accept_trade, decline_trade)
from actions.items import tavern, tavern_cb, armory, armory_cb
from users.registration import start, getNickname, send_info, confirm_nickname, command_error, NICKNAME, CONFIRM_NICKNAME, INFOS
from users.profile import profile, office, office_cb
from users.stats import stats, stats_cb, rankup_cb
from users.inventory import (inventory, inventory_cb, info, sell, use, equip, equipment, unequip, start_crafting,
                             potion_selection, confirm_crafting, back_to_potions)
from users.guild import found, guild, setGuild, members, members_cb, invite, invite_cb, promote, degrade, kickout, leave
from utils.general import guide, top, top_cb, reset, reset_cb

travel_cb_pattern = re.compile(r'^[RA]')


async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """message handler to update some variables"""
    conn = sqlite3.connect("dungeon.db")
    c = conn.cursor()

    try:
        user_id = update.effective_message.from_user.id

        if update.message.text.startswith('/'):
            return

        if c.execute("SELECT COUNT(*) FROM Messages WHERE user_id = ?", (user_id,)).fetchone()[0] == 0:
            conn.close()
            return


        bounty = c.execute("SELECT bounty FROM User WHERE user_id = ?", (user_id,)).fetchone()[0]
        c.execute("UPDATE Guild SET bounty = ? WHERE user_id = ?", (bounty, user_id))

        c.execute("UPDATE Messages SET num_msg = num_msg + 1 WHERE user_id = ?", (user_id,))

        if update.message.chat.type == 'private':
            c.execute("UPDATE User SET chat_id = ? WHERE user_id = ?", (update.message.chat_id, user_id))

        conn.commit()

        numMessages = c.execute("SELECT num_msg FROM Messages WHERE user_id = ?", (user_id,)).fetchone()[0]
        if numMessages % 15 == 1:
            c.execute("UPDATE User SET exp = exp + 1 WHERE user_id = ?", (user_id,))
        conn.commit()

    except Exception as e:
        print(f"Error during message handling: {e}")

    finally:
        conn.close()


def register_handlers(application):
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NICKNAME: [MessageHandler(filters.TEXT, getNickname)],
            CONFIRM_NICKNAME: [MessageHandler(filters.TEXT, confirm_nickname)],
            INFOS: [MessageHandler(filters.TEXT, send_info)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, command_error)],
    ))

    application.add_handler(CommandHandler('office', office))
    application.add_handler(CallbackQueryHandler(office_cb, pattern='swordsman'))
    application.add_handler(CallbackQueryHandler(office_cb, pattern='archer'))
    application.add_handler(CallbackQueryHandler(office_cb, pattern='acolyte'))
    application.add_handler(CallbackQueryHandler(office_cb, pattern='thief'))

    application.add_handler(CallbackQueryHandler(rankup_cb, pattern='knight'))
    application.add_handler(CallbackQueryHandler(rankup_cb, pattern='royal_guard'))
    application.add_handler(CallbackQueryHandler(rankup_cb, pattern='hunter'))
    application.add_handler(CallbackQueryHandler(rankup_cb, pattern='ranger'))
    application.add_handler(CallbackQueryHandler(rankup_cb, pattern='mage'))
    application.add_handler(CallbackQueryHandler(rankup_cb, pattern='alchemist'))
    application.add_handler(CallbackQueryHandler(rankup_cb, pattern='assassin'))
    application.add_handler(CallbackQueryHandler(rankup_cb, pattern='burglar'))

    application.add_handler(CommandHandler('profile', profile))

    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(CallbackQueryHandler(stats_cb, pattern='hp'))
    application.add_handler(CallbackQueryHandler(stats_cb, pattern='atk'))
    application.add_handler(CallbackQueryHandler(stats_cb, pattern='def'))
    application.add_handler(CallbackQueryHandler(stats_cb, pattern='vel'))
    application.add_handler(CallbackQueryHandler(stats_cb, pattern='stats'))


    application.add_handler(CommandHandler('travel', travel))
    application.add_handler(CallbackQueryHandler(travel_cb, pattern=travel_cb_pattern))

    application.add_handler(CommandHandler('explore', explore))

    application.add_handler(CommandHandler("battle", battle))
    application.add_handler(CallbackQueryHandler(continue_battle, pattern='continue_battle'))
    application.add_handler(CallbackQueryHandler(flee_battle, pattern='flee_battle'))

    application.add_handler(CommandHandler('inventory', inventory))
    application.add_handler(CallbackQueryHandler(inventory_cb, pattern='^page:'))

    application.add_handler(CommandHandler('info', info))
    application.add_handler(CommandHandler('sell', sell))

    application.add_handler(CommandHandler('tavern', tavern))
    application.add_handler(CallbackQueryHandler(tavern_cb, pattern='^tavern_option'))

    application.add_handler(CommandHandler('armory', armory))
    application.add_handler(CallbackQueryHandler(armory_cb, pattern="^armory|buy_item|back_to_armory"))

    application.add_handler(CommandHandler('equip', equip))
    application.add_handler(CommandHandler('equipment', equipment))
    application.add_handler(CommandHandler('unequip', unequip))

    application.add_handler(CommandHandler("craft", start_crafting))
    application.add_handler(CallbackQueryHandler(potion_selection, pattern='^craft_'))
    application.add_handler(CallbackQueryHandler(confirm_crafting, pattern='^confirm_craft_'))
    application.add_handler(CallbackQueryHandler(back_to_potions, pattern='^back_to_potions$'))

    application.add_handler(CommandHandler('use', use))

    application.add_handler(CommandHandler("trade", start_trade))
    application.add_handler(CallbackQueryHandler(join_trade, pattern="^join_trade_"))
    application.add_handler(CallbackQueryHandler(continue_trade, pattern="^continue_trade_"))
    application.add_handler(CallbackQueryHandler(add_item, pattern="^add_item_"))
    application.add_handler(CallbackQueryHandler(select_item, pattern="^select_item_"))
    application.add_handler(CallbackQueryHandler(add_gold, pattern="^add_gold_"))
    application.add_handler(CallbackQueryHandler(back_to_trade, pattern="^back_to_trade_"))
    application.add_handler(CallbackQueryHandler(confirm_offer, pattern="^confirm_offer_"))
    application.add_handler(CallbackQueryHandler(accept_trade, pattern="^accept_trade_"))
    application.add_handler(CallbackQueryHandler(decline_trade, pattern="^decline_trade_"))
    application.add_handler(CallbackQueryHandler(cancel_trade, pattern="^cancel_trade_"))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_item_quantity), group=1)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_gold_amount), group=2)

    application.add_handler(CommandHandler('found', found))
    application.add_handler(CommandHandler('guild', guild))
    application.add_handler(CommandHandler('rename', setGuild))

    application.add_handler(CommandHandler('members', members))
    application.add_handler(CallbackQueryHandler(members_cb, pattern='^members_page:'))

    application.add_handler(CommandHandler('invite', invite))
    application.add_handler(CallbackQueryHandler(invite_cb, pattern='accept'))
    application.add_handler(CallbackQueryHandler(invite_cb, pattern='decline'))

    application.add_handler(CommandHandler('promote', promote))
    application.add_handler(CommandHandler('degrade', degrade))
    application.add_handler(CommandHandler('expel', kickout))
    application.add_handler(CommandHandler('leave', leave))

    application.add_handler(CommandHandler('guide', guide))

    application.add_handler(CommandHandler('top', top))
    application.add_handler(CallbackQueryHandler(top_cb, pattern='lvl'))
    application.add_handler(CallbackQueryHandler(top_cb, pattern='bounty'))
    application.add_handler(CallbackQueryHandler(top_cb, pattern='guilds'))
    application.add_handler(CallbackQueryHandler(top_cb, pattern='top'))

    application.add_handler(CommandHandler('players', players))

    application.add_handler(CommandHandler('add', addGold))
    application.add_handler(CommandHandler('increase', addLvl))
    application.add_handler(CommandHandler('ban', ban))
    application.add_handler(CommandHandler('unban', unban))

    application.add_handler(CommandHandler('reset', reset))
    application.add_handler(CallbackQueryHandler(reset_cb, pattern='yes'))
    application.add_handler(CallbackQueryHandler(reset_cb, pattern='no'))

    application.add_handler(CommandHandler('announce', announce))
    application.add_handler(CommandHandler('restore', restorationGuild))

    application.add_handler(MessageHandler(filters.TEXT, messages))
