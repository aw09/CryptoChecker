import os
import pandas as pd
from datetime import datetime
import streamlit as st
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import textwrap
from functools import wraps
from gate_script import get_balance, get_spot_holdings
import logging
import asyncio
from db_utils import (register_user, add_api_key, get_user_api_keys, 
                     set_alert, get_user_alerts)

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

@authorization
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if await register_user(user.id, user.username):
        await update.message.reply_text(
            "Welcome to Crypto Checker Bot!\n\n"
            "Commands:\n"
            "/addapi - Add Gate.io API keys\n"
            "/myapis - List your API keys\n"
            "/addalert - Create price alert\n"
            "/alerts - List your alerts\n"
            "/info - Get balance info\n"
            "/holdings - Get holdings info"
        )
    else:
        await update.message.reply_text("Error registering user. Please try again.")

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

async def alert_coin_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['coin'] = update.message.text.upper()
    await update.message.reply_text("Choose condition (< or >):")
    return ALERT_CONDITION

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
        # Send processing message
        processing_msg = await update.message.reply_text("Processing...")
        
        # Get balances
        balances = get_balance()
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
        processing_msg = await update.message.reply_text("Processing...")
        all_holdings = get_spot_holdings(min_usdt_value=0.5)
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
        
        message = "Your API Keys:\n\n"
        for i, api in enumerate(apis, 1):
            message += f"{i}. {api['name']}\n"
            message += f"   Added: {api['added_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error showing APIs: {e}")
        await update.message.reply_text("Error fetching your API keys.")

# Global application instance
application = None

def main():
    logger.info("Starting Telegram bot...")
    
    app = ApplicationBuilder().token(st.secrets["telegram"]["token"]).build()
    
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

    # Add conversation handler for alerts
    alert_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('addalert', add_alert_start)],
        states={
            ALERT_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, alert_coin_received)],
            ALERT_CONDITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, alert_condition_received)],
            ALERT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, alert_price_received)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(api_conv_handler)
    app.add_handler(alert_conv_handler)
    app.add_handler(CommandHandler("myapis", show_my_apis))  # Add this line
    app.add_handler(CommandHandler("info", sendInfo))
    app.add_handler(CommandHandler("holdings", sendHoldings))  # Add new handler
    
    logger.info("Bot initialization complete, starting polling...")
    app.run_polling(poll_interval=3.0)

if __name__ == '__main__':
    # Make sure streamlit is initialized when running directly
    if not hasattr(st, 'secrets'):
        st.runtime.get_instance().get_cached_resource("secrets")
    main()