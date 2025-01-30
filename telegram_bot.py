import os
import pandas as pd
from datetime import datetime
import streamlit as st
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
import textwrap
from functools import wraps
from gate_script import check_ticker_exists
import logging
import asyncio
from db_utils import (register_user, add_api_key, get_user_api_keys, 
                     set_alert, get_user_alerts, delete_api_key, set_selected_api, get_selected_api)
from handlers.alert_handlers import (
    add_alert_start, alert_coin_received, alert_condition_received,
    alert_price_received, show_alerts, cancel_alert,
    ALERT_COIN, ALERT_CONDITION, ALERT_PRICE
)
from handlers.api_handlers import (
    add_api_start, add_api_key_received, add_api_secret_received,
    add_api_name_received, show_my_apis, handle_api_deletion,
    handle_api_selection, APIKEY, APISECRET, APINAME
)
from handlers.balance_handlers import sendInfo, sendHoldings

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

@authorization
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if await register_user(user.id, user.username):
        await show_main_menu(update, context)
    else:
        await update.message.reply_text("Error registering user. Please try again.")

@authorization
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [KeyboardButton("💰 Balance"), KeyboardButton("📊 Holdings")],
        [KeyboardButton("🔑 Add API"), KeyboardButton("🔐 My APIs")],
        [KeyboardButton("🎯 Add Alert"), KeyboardButton("🔔 My Alerts")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome to Crypto Checker Bot!\n"
        "Please select an option:",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages and menu buttons"""
    text = update.message.text
    
    if text == "💰 Balance":
        await sendInfo(update, context)
    elif text == "📊 Holdings":
        await sendHoldings(update, context)
    elif text == "🔑 Add API":
        await add_api_start(update, context)
    elif text == "🔐 My APIs":
        await show_my_apis(update, context)
    elif text == "🎯 Add Alert":
        await add_alert_start(update, context)
    elif text == "🔔 My Alerts":
        await show_alerts(update, context)

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
    """Async function to run the bot"""
    global _running
    if _running:
        return

    _running = True
    app = get_application()
    try:
        # Remove manual initialize/start calls
        await app.run_polling(poll_interval=3.0, drop_pending_updates=True)
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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", show_main_menu))
    app.add_handler(alert_conv_handler)
    app.add_handler(api_conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_api_deletion, pattern="^delete_api_"))
    app.add_handler(CallbackQueryHandler(handle_api_selection, pattern="^select_api_"))
