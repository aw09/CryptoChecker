import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from db_utils import set_alert, get_user_alerts, get_selected_api
from gate_script import check_ticker_exists
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, ReplyKeyboardMarkup, KeyboardButton
import asyncio
import streamlit as st
from gate_script import check_current_price
from datetime import datetime
import pymongo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname%s - %(message)s'
)
logger = logging.getLogger(__name__)

# States for alert conversation
ALERT_COIN, ALERT_CONDITION, ALERT_PRICE = range(3)

async def add_alert_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Which coin do you want to track? (e.g., BTC)")
    return ALERT_COIN

async def alert_coin_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        coin = update.message.text.upper()
        logger.info(f"Checking coin: {coin}")
        
        selected_api = await get_selected_api(update.effective_user.id)
        if not selected_api:
            await update.message.reply_text("Please select an API first using 🔐 My APIs")
            return ConversationHandler.END
        
        if not check_ticker_exists(selected_api['api_key'], selected_api['api_secret'], coin):
            await update.message.reply_text(f"❌ Error: Could not find ticker for {coin}/USDT\nPlease check the coin symbol and try again.")
            return ConversationHandler.END
        
        logger.info(f"Ticker {coin}/USDT exists, proceeding")
        context.user_data['coin'] = coin
        keyboard = [[KeyboardButton("<"), KeyboardButton(">")]]
        await update.message.reply_text(
            "Choose condition:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
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

async def show_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def cancel_alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Alert creation cancelled.')
    return ConversationHandler.END

async def check_alerts(bot):
    """Worker function to check alerts periodically"""
    logger.info("Starting alert checker worker")
    while True:
        try:
            # Get all alerts from database
            all_alerts = await get_user_alerts(None)  # None to get all users' alerts
            logger.info(f"Retrieved {len(all_alerts)} total alerts.")
            if not all_alerts:
                logger.info("No alerts found, waiting...")
                await asyncio.sleep(60)
                continue
            
            for alert in all_alerts:
                try:
                    logger.info(f"Checking alert {alert['_id']}")
                    # Get user's selected API for price checking
                    selected_api = await get_selected_api(alert['user_id'])
                    if not selected_api:
                        continue
                    
                    current_price = check_current_price(
                        selected_api['api_key'],
                        selected_api['api_secret'],
                        alert['coin']
                    )
                    
                    condition_met = False
                    if alert['condition'] == '<' and current_price < alert['price']:
                        condition_met = True
                    elif alert['condition'] == '>' and current_price > alert['price']:
                        condition_met = True
                    
                    if condition_met:
                        message = (
                            f"🚨 Alert Triggered!\n"
                            f"Coin: {alert['coin']}\n"
                            f"Condition: {alert['condition']} {alert['price']}\n"
                            f"Current Price: {current_price}\n"
                            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        try:
                            await bot.send_message(chat_id=alert['user_id'], text=message)
                            # Mark it inactive
                            db = pymongo.MongoClient(st.secrets["mongodb"]["url"]).crypto_checker
                            db.alerts.update_one({"_id": alert["_id"]}, {"$set": {"active": False}})
                        except Exception as e:
                            logger.error(f"Failed to send alert to user {alert['user_id']}: {e}")
                        
                except Exception as e:
                    logger.error(f"Error checking alert {alert['_id']}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error in alert checker: {e}")
        
        await asyncio.sleep(60)  # Wait between checks
