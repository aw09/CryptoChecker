import os
import pandas as pd
from datetime import datetime
import streamlit as st
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import textwrap
from functools import wraps
from gate_script import get_balance
import logging
import asyncio

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

# Global application instance
application = None

def main():
    logger.info("Starting Telegram bot...")
    
    app = ApplicationBuilder().token(st.secrets["telegram"]["token"]).build()
    app.add_handler(CommandHandler("info", sendInfo))
    
    logger.info("Bot initialization complete, starting polling...")
    app.run_polling(poll_interval=3.0)

if __name__ == '__main__':
    # Make sure streamlit is initialized when running directly
    if not hasattr(st, 'secrets'):
        st.runtime.get_instance().get_cached_resource("secrets")
    main()