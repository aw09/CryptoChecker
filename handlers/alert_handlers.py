import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from db_utils import set_alert, get_user_alerts, get_selected_api
from gate_script import check_ticker_exists
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, ReplyKeyboardMarkup, KeyboardButton

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
