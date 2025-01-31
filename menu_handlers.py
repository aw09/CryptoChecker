from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ContextTypes,
)
from functools import wraps
from gate_script import check_ticker_exists
from db_utils import (
    register_user,
)
from handlers.alert_handlers import (
    add_alert_start,
    show_alerts,
)
from handlers.api_handlers import (
    add_api_start,
    show_my_apis,
)
from handlers.trade_handlers import start_buy_flow, handle_sell_all
from handlers.balance_handlers import sendInfo, sendHoldings, sendEarn


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [KeyboardButton("💰 Balance"), KeyboardButton("📊 Holdings")],
        [KeyboardButton("💎 Earn"), KeyboardButton("💵 Buy")],
        [KeyboardButton("🎯 Add Alert"), KeyboardButton("🔔 My Alerts")],
        [KeyboardButton("🔑 Add API"), KeyboardButton("🔐 My APIs")],
        [KeyboardButton("❌ SELL ALL")]  # Add this line
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome to Crypto Checker Bot!\nPlease select an option:",
        reply_markup=reply_markup,
    )


# @authorization
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if await register_user(user.id, user.username):
        await show_main_menu(update, context)
    else:
        await update.message.reply_text("Error registering user. Please try again.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages and menu buttons"""
    text = update.message.text

    if text == "💵 Buy":
        await start_buy_flow(update, context)
    elif text == "💰 Balance":
        await sendInfo(update, context)
    elif text == "📊 Holdings":
        await sendHoldings(update, context)
    elif text == "💎 Earn":
        await sendEarn(update, context)
    elif text == "🔑 Add API":
        await add_api_start(update, context)
    elif text == "🔐 My APIs":
        await show_my_apis(update, context)
    elif text == "🎯 Add Alert":
        await add_alert_start(update, context)
    elif text == "🔔 My Alerts":
        await show_alerts(update, context)
    elif text == "❌ SELL ALL":
        await handle_sell_all(update, context)
