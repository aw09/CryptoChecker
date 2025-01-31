import os
import pandas as pd
from datetime import datetime
import streamlit as st
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from functools import wraps
from gate_script import check_ticker_exists

import logging

from handlers.alert_handlers import (
    add_alert_start, alert_coin_received, alert_condition_received,
    alert_price_received, cancel_alert,
    ALERT_COIN, ALERT_CONDITION, ALERT_PRICE
)
from handlers.api_handlers import (
    add_api_start, add_api_key_received, add_api_secret_received,
    add_api_name_received, handle_api_deletion,
    handle_api_selection, show_api_detail, back_to_apis,
    APIKEY, APISECRET, APINAME
)
from handlers.balance_handlers import (
    refresh_balance, refresh_holdings, refresh_earn
)
from menu_handlers import show_main_menu, start, handle_message
from handlers.trade_handlers import (
    start_buy, start_sell, execute_trade, cancel_trade,
    handle_sell_amount_option, handle_sell_percentage, 
    start_buy_flow, handle_sell_usdt_option,
    TRADE_AMOUNT, TRADE_PERCENTAGE
)

# Configure logging with proper format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = st.secrets["telegram"]["token"]
def read_whitelist():
    return st.secrets["whitelist"]["usernames"]

def authorization(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.username not in read_whitelist() and str(update.effective_user.id) not in read_whitelist():
            await update.message.reply_text('You are not authorized to use this bot.')
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# Add states for conversation
APIKEY, APISECRET, APINAME = range(3)

async def setup_commands(application):
    """Setup bot commands in the menu"""
    commands = [
        BotCommand("start", "Start the bot and show main menu"),
        BotCommand("menu", "Show main menu")
    ]
    await application.bot.set_my_commands(commands)

# Global variables
application = None
_initialized = False
_running = False

def get_application():
    global application, _initialized
    if application is None:
        application = ApplicationBuilder().token(st.secrets["telegram"]["token"]).build()
        if not _initialized:
            setup_handlers(application)
            _initialized = True
    return application

async def run_bot():
    global _running
    if _running:
        return
    _running = True
    app = get_application()
    try:
        # Run polling without signals
        await app.run_polling(
            poll_interval=3.0,
            drop_pending_updates=True,
            stop_signals=None,
            close_loop=False
        )
    finally:
        _running = False

def setup_handlers(app):
    """Setup all handlers for the application"""
    # Add conversation handler for API keys
    api_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('addapi', add_api_start),
            MessageHandler(filters.Regex('^🔑 Add API$'), add_api_start)
        ],
        states={
            APIKEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_api_key_received)],
            APISECRET: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_api_secret_received)],
            APINAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_api_name_received)],
        },
        fallbacks=[],
    )

    # Add conversation handler for alerts with both command and button handlers
    alert_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('addalert', add_alert_start),
            MessageHandler(filters.Regex('^🎯 Add Alert$'), add_alert_start)
        ],
        states={
            ALERT_COIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex('^🎯 Add Alert$'), alert_coin_received)
            ],
            ALERT_CONDITION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, alert_condition_received)
            ],
            ALERT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, alert_price_received)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_alert)],
        name='alert_conversation'
    )

    # Update trade handler with fixed patterns
    trade_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_buy, pattern=r'^buy_[A-Z0-9]+$'),
            CallbackQueryHandler(start_sell, pattern=r'^sell_[A-Z0-9]+$'),
            MessageHandler(filters.Regex('^💵 Buy$'), start_buy_flow)
        ],
        states={
            TRADE_PERCENTAGE: [
                CallbackQueryHandler(handle_sell_percentage, pattern=r'^sellpct_[A-Z0-9]+_\d+$'),
                CallbackQueryHandler(handle_sell_usdt_option, pattern=r'^sellusdt_[A-Z0-9]+$'),
                CallbackQueryHandler(handle_sell_amount_option, pattern=r'^sellamt_[A-Z0-9]+$')
            ],
            TRADE_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, execute_trade)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_trade)],
        name='trade_conversation',
        per_message=True  # Add this line
    )
    
    # Important: Remove any existing handlers before adding new ones
    app.handlers.clear()
    
    # Add all handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", show_main_menu))
    app.add_handler(alert_conv_handler)
    app.add_handler(api_conv_handler)
    app.add_handler(trade_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(show_api_detail, pattern="^api_detail_"))
    app.add_handler(CallbackQueryHandler(handle_api_deletion, pattern="^delete_api_"))
    app.add_handler(CallbackQueryHandler(handle_api_selection, pattern="^select_api_"))
    app.add_handler(CallbackQueryHandler(refresh_balance, pattern="^refresh_balance$"))  # Add this line
    app.add_handler(CallbackQueryHandler(refresh_holdings, pattern="^refresh_holdings$"))
    app.add_handler(CallbackQueryHandler(back_to_apis, pattern="^back_to_apis$"))
    app.add_handler(CallbackQueryHandler(refresh_earn, pattern="^refresh_earn$"))

