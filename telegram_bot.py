import os
import pandas as pd
from datetime import datetime
import streamlit as st
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import textwrap
from functools import wraps
from gate_script import get_balance

TELEGRAM_TOKEN = st.secrets["telegram"]["token"]
filename = 'balance_vs_btc.csv'
refresh_time = 3 * 60  # 3 minutes

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

async def updateData(*args, **kwargs):
    return get_balance()

@authorization
async def sendInfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    balances = await updateData()
    
    message_parts = [f"{datetime.now()}\n"]
    total = balances.pop('total')  # Remove and store total
    
    for account, data in balances.items():
        message_parts.append(f"=== {data['name']} ===\n"
                           f"Total Asset in USDT: {format(data['balance'], ',.2f')}\n")
    
    message = '\n'.join(message_parts)
    await update.message.reply_text(message)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("info", sendInfo))
    app.job_queue.run_repeating(updateData, interval=refresh_time, first=0)
    app.run_polling()

if __name__ == '__main__':
    main()
