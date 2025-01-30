import os
import pandas as pd
from datetime import datetime
import streamlit as st
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
import textwrap
from functools import wraps
from gate_script import get_balance, get_spot_holdings, check_ticker_exists
import logging
import asyncio
from db_utils import (register_user, add_api_key, get_user_api_keys, 
                     set_alert, get_user_alerts, delete_api_key, set_selected_api, get_selected_api)

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
ALERT_COIN, ALERT_CONDITION, ALERT_PRICE = range(3, 6)

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

@authorization
async def show_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's active alerts"""
    alerts = await get_user_alerts(update.effective_user.id)
    if not alerts:
        await update.message.reply_text("You don't have any active alerts.")
        return
    
    message = "Your Active Alerts:\n\n"
    for alert in alerts:
        message += f"🎯 {alert['coin']}: {alert['condition']} {alert['price']} USDT\n"
    
    keyboard = []
    for alert in alerts:
        keyboard.append([
            InlineKeyboardButton(
                f"❌ Delete {alert['coin']} Alert", 
                callback_data=f"delete_alert_{alert['_id']}"
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup)

async def add_api_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please send your Gate.io API key:")
    return APIKEY

async def add_api_key_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['api_key'] = update.message.text
    await update.message.reply_text("Now send your API secret:")
    return APISECRET

async def add_api_secret_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['api_secret'] = update.message.text
    await update.message.reply_text("Give a name for this API (e.g., 'Main Account'):")
    return APINAME

async def add_api_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if await add_api_key(
        update.effective_user.id,
        update.message.text,
        context.user_data['api_key'],
        context.user_data['api_secret']
    ):
        await update.message.reply_text("API keys added successfully!")
    else:
        await update.message.reply_text("Error adding API keys. Please try again.")
    return ConversationHandler.END

@authorization
async def add_alert_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Which coin do you want to track? (e.g., BTC)")
    return ALERT_COIN

@authorization
async def alert_coin_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        coin = update.message.text.upper()
        logger.info(f"Checking coin: {coin}")
        
        # Get selected API for ticker validation
        selected_api = await get_selected_api(update.effective_user.id)
        if not selected_api:
            await update.message.reply_text("Please select an API first using 🔐 My APIs")
            return ConversationHandler.END
        
        # Check if ticker exists
        logger.info(f"Validating ticker for {coin}/USDT")
        if not check_ticker_exists(selected_api['api_key'], selected_api['api_secret'], coin):
            await update.message.reply_text(f"❌ Error: Could not find ticker for {coin}/USDT\nPlease check the coin symbol and try again.")
            return ConversationHandler.END
        
        logger.info(f"Ticker {coin}/USDT exists, proceeding")
        context.user_data['coin'] = coin
        await update.message.reply_text("Choose condition (< or >):")
        return ALERT_CONDITION
        
    except Exception as e:
        logger.error(f"Error in alert_coin_received: {e}")
        await update.message.reply_text("An error occurred. Please try again.")
        return ConversationHandler.END

async def alert_condition_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text not in ['<', '>']:
        await update.message.reply_text("Please send either < or >")
        return ALERT_CONDITION
    context.user_data['condition'] = update.message.text
    await update.message.reply_text("Enter price in USDT:")
    return ALERT_PRICE

async def alert_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        price = float(update.message.text)
        if await set_alert(
            update.effective_user.id,
            context.user_data['coin'],
            context.user_data['condition'],
            price
        ):
            await update.message.reply_text("Alert set successfully!")
        else:
            await update.message.reply_text("Error setting alert. Please try again.")
    except ValueError:
        await update.message.reply_text("Please enter a valid number")
        return ALERT_PRICE
    return ConversationHandler.END

@authorization
async def sendInfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Received command from {update.effective_user.username}")

    try:
        # Get selected API with debug logging
        selected_api = await get_selected_api(update.effective_user.id)
        print(f"Selected API: {selected_api['name'] if selected_api else 'None'}")
        
        if not selected_api:
            await update.message.reply_text("Please select an API first using /selectapi")
            return

        # Send processing message
        processing_msg = await update.message.reply_text("Processing...")
        
        # Get balances using selected API
        print(f"Getting balance for API: {selected_api['name']}")
        balances = get_balance(api_key=selected_api['api_key'], 
                             api_secret=selected_api['api_secret'])
        total = balances.pop('total')
        
        # Build message
        message_parts = [f"{datetime.now()}\n"]
        for account, data in balances.items():
            message_parts.append(f"=== {data['name']} ===\n"
                               f"Total Asset in USDT: {format(data['balance'], ',.2f')}\n")
        
        # Add total
        message_parts.append(f"\n=== TOTAL ===\n"
                           f"Total Asset in USDT: {format(total, ',.2f')}")
        
        # Send final message
        await update.message.reply_text('\n'.join(message_parts))
        
        # Delete processing message
        await processing_msg.delete()
        
    except Exception as e:
        await update.message.reply_text(f"Error getting balances: {str(e)}")

@authorization
async def sendHoldings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Received holdings command from {update.effective_user.username}")

    try:
        selected_api = await get_selected_api(update.effective_user.id)
        if not selected_api:
            await update.message.reply_text("Please select an API first using /selectapi")
            return

        processing_msg = await update.message.reply_text("Processing...")
        all_holdings = get_spot_holdings(api_key=selected_api['api_key'],
                                       api_secret=selected_api['api_secret'],
                                       min_usdt_value=0.5)
        message_parts = [f"{datetime.now()}\n"]
        
        account_total_usdt = {}
        
        for account_name, data in all_holdings.items():
            message_parts.append(f"\n=== {data['name']} ===")
            if not data['holdings']:
                message_parts.append("No holdings found")
                continue
            
            account_total = 0
            for holding in data['holdings']:
                account_total += holding['value_usdt']
                message_parts.append(
                    f"\n{holding['currency']}:"
                    f"\n  Amount: {format(holding['total'], '.8f')}"
                    f"\n  Price: {format(holding['price_usdt'], '.4f')} USDT"
                    f"\n  Value: {format(holding['value_usdt'], '.2f')} USDT"
                )
            
            account_total_usdt[account_name] = account_total
            message_parts.append(f"\nSubtotal: {format(account_total, '.2f')} USDT")
        
        # Add grand total
        grand_total = sum(account_total_usdt.values())
        message_parts.append(f"\n=== GRAND TOTAL ===\n{format(grand_total, '.2f')} USDT")
        
        # Split and send message
        full_message = '\n'.join(message_parts)
        if len(full_message) > 4000:
            chunks = textwrap.wrap(full_message, 4000)
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(full_message)
        
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"Error getting holdings: {str(e)}")
        await update.message.reply_text(f"Error getting holdings: {str(e)}")

@authorization
async def show_my_apis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        apis = await get_user_api_keys(update.effective_user.id)
        if not apis:
            await update.message.reply_text("You haven't added any API keys yet.\nUse /addapi to add one.")
            return
        
        keyboard = []
        for api in apis:
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑️ Delete {api['name']}", 
                    callback_data=f"delete_api_{api['name']}"
                )
            ])
        
        message = "Your API Keys:\n\n"
        for i, api in enumerate(apis, 1):
            message += f"{i}. {api['name']}\n"
            message += f"   Added: {api['added_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error showing APIs: {e}")
        await update.message.reply_text("Error fetching your API keys.")

async def handle_api_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    # Extract API name from callback data
    api_name = query.data.replace("delete_api_", "")
    
    if await delete_api_key(query.from_user.id, api_name):
        await query.edit_message_text(f"Successfully deleted API key: {api_name}")
    else:
        await query.edit_message_text(f"Failed to delete API key: {api_name}")

@authorization
async def select_api(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        apis = await get_user_api_keys(update.effective_user.id)
        if not apis:
            await update.message.reply_text("You haven't added any API keys yet.\nUse /addapi to add one.")
            return
        
        keyboard = []
        for api in apis:
            keyboard.append([
                InlineKeyboardButton(
                    f"📌 Select {api['name']}", 
                    callback_data=f"select_api_{api['name']}"
                )
            ])
        
        selected_api = await get_selected_api(update.effective_user.id)
        message = "Select API to use:\n\n"
        if selected_api:
            message += f"Currently using: {selected_api['name']}\n\n"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error showing API selection: {e}")
        await update.message.reply_text("Error fetching your APIs.")

async def handle_api_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    api_name = query.data.replace("select_api_", "")
    if await set_selected_api(query.from_user.id, api_name):
        await query.edit_message_text(f"Successfully selected API: {api_name}")
    else:
        await query.edit_message_text(f"Failed to select API: {api_name}")

# Global application instance
application = None

def main():
    logger.info("Starting Telegram bot...")
    
    app = ApplicationBuilder().token(st.secrets["telegram"]["token"]).build()
    
    # Setup commands menu
    asyncio.get_event_loop().run_until_complete(setup_commands(app))
    
    # Add conversation handler for API keys
    api_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('addapi', add_api_start)],
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
    app.add_handler(alert_conv_handler)  # Move this before the general message handler
    app.add_handler(api_conv_handler)
    app.add_handler(CommandHandler("myapis", show_my_apis))  # Add this line
    app.add_handler(CommandHandler("selectapi", select_api))
    app.add_handler(CommandHandler("info", sendInfo))
    app.add_handler(CommandHandler("holdings", sendHoldings))  # Add new handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_api_deletion, pattern="^delete_api_"))  # Add callback query handler for API deletion
    app.add_handler(CallbackQueryHandler(handle_api_selection, pattern="^select_api_"))

    logger.info("Bot initialization complete, starting polling...")
    app.run_polling(poll_interval=3.0)

async def cancel_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Alert creation cancelled.')
    return ConversationHandler.END

if __name__ == '__main__':
    # Make sure streamlit is initialized when running directly
    if not hasattr(st, 'secrets'):
        st.runtime.get_instance().get_cached_resource("secrets")
    main()