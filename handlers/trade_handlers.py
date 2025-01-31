import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from gate_script import buy_spot, sell_spot, get_spot_holdings
from db_utils import get_selected_api

# Add new state for percentage selection
TRADE_AMOUNT, TRADE_PERCENTAGE = range(2)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_coin_from_callback(callback_data: str) -> str:
    """Extract coin name from callback data, handling USDT pairs"""
    parts = callback_data.split('_')
    if len(parts) < 2:
        raise ValueError("Invalid callback data format")
    
    # Handle cases like "buy_USDT" or "sell_USDT"
    if len(parts) == 2 and parts[1] == "USDT":
        return "USDT"
    
    # Handle cases like "buy_BTC_USDT" or "sell_ETH_USDT"
    if len(parts) == 3 and parts[2] == "USDT":
        return parts[1]
    
    # Default case for normal coins
    return parts[1]

async def start_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        query = update.callback_query
        coin = extract_coin_from_callback(query.data)
        context.user_data['trade_coin'] = coin
        context.user_data['trade_type'] = 'buy'
        
        await query.answer()
        await query.edit_message_text(
            f"How many {coin} would you like to buy?\n"
            "Please enter the amount in USDT or /cancel to abort."
        )
        return TRADE_AMOUNT
    except Exception as e:
        logger.error(f"Error in start_buy: {str(e)}")
        await query.edit_message_text(f"Error starting buy: {str(e)}")
        return ConversationHandler.END

async def start_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        query = update.callback_query
        coin = extract_coin_from_callback(query.data)
        context.user_data['trade_coin'] = coin
        context.user_data['trade_type'] = 'sell'
        
        keyboard = [
            [
                InlineKeyboardButton("25%", callback_data=f"sellpct_{coin}_25"),
                InlineKeyboardButton("50%", callback_data=f"sellpct_{coin}_50"),
                InlineKeyboardButton("75%", callback_data=f"sellpct_{coin}_75"),
                InlineKeyboardButton("100%", callback_data=f"sellpct_{coin}_100")
            ],
            [InlineKeyboardButton("Enter custom amount", callback_data=f"sellamt_{coin}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer()
        await query.edit_message_text(
            f"How would you like to sell {coin}?",
            reply_markup=reply_markup
        )
        return TRADE_PERCENTAGE
    except Exception as e:
        logger.error(f"Error in start_sell: {str(e)}")
        await query.edit_message_text(f"Error starting sell: {str(e)}")
        return ConversationHandler.END

async def handle_sell_percentage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    try:
        # Parse the callback data
        parts = query.data.split('_')
        if len(parts) != 3:
            raise ValueError("Invalid callback data format")
        
        coin = parts[1]
        percentage = float(parts[2])
        
        # Get current holdings
        selected_api = await get_selected_api(update.effective_user.id)
        if not selected_api:
            await query.edit_message_text("Please select an API first using 🔐 My APIs")
            return ConversationHandler.END
            
        holdings = get_spot_holdings(
            api_key=selected_api['api_key'],
            api_secret=selected_api['api_secret']
        )
        
        # Find the coin balance
        coin_balance = 0
        for account in holdings.values():
            for holding in account['holdings']:
                if holding['currency'] == coin:
                    coin_balance = holding['total']
                    break
        
        if coin_balance == 0:
            await query.edit_message_text(f"No {coin} balance found.")
            return ConversationHandler.END
        
        # Calculate the amount to sell
        sell_amount = coin_balance * (percentage / 100)
        
        # Execute the sell order
        result = sell_spot(
            api_key=selected_api['api_key'],
            api_secret=selected_api['api_secret'],
            currency=coin,
            amount=sell_amount
        )
        
        await query.edit_message_text(
            f"Sell order executed successfully!\n"
            f"Amount: {sell_amount:.8f} {coin} ({percentage}% of {coin_balance:.8f})\n"
            f"Order ID: {result['order_id']}\n"
            f"Status: {result['status']}"
        )
        
    except Exception as e:
        logger.error(f"Error in handle_sell_percentage: {str(e)}")
        await query.edit_message_text(f"Error executing trade: {str(e)}")
        return ConversationHandler.END

async def handle_sell_amount_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    try:
        coin = extract_coin_from_callback(query.data)
        context.user_data['trade_coin'] = coin
        
        await query.edit_message_text(
            f"How many {coin} would you like to sell?\n"
            "Please enter the amount or /cancel to abort."
        )
        return TRADE_AMOUNT
    except Exception as e:
        logger.error(f"Error in handle_sell_amount_option: {str(e)}")
        await query.edit_message_text(f"Error setting up sell amount: {str(e)}")
        return ConversationHandler.END

async def execute_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = float(update.message.text)
        coin = context.user_data['trade_coin']
        trade_type = context.user_data['trade_type']
        
        selected_api = await get_selected_api(update.effective_user.id)
        if not selected_api:
            await update.message.reply_text("Please select an API first using 🔐 My APIs")
            return ConversationHandler.END

        # Execute the trade using the appropriate function
        if trade_type == 'buy':
            result = buy_spot(
                api_key=selected_api['api_key'],
                api_secret=selected_api['api_secret'],
                currency=coin,
                amount=amount  # For market buy, amount is in USDT
            )
        else:  # sell
            result = sell_spot(
                api_key=selected_api['api_key'],
                api_secret=selected_api['api_secret'],
                currency=coin,
                amount=amount  # For sell, amount is in the base currency
            )

        await update.message.reply_text(
            f"{trade_type.title()} order executed successfully!\n"
            f"Amount: {amount} {'USDT' if trade_type == 'buy' else coin}\n"
            f"Order ID: {result['order_id']}\n"
            f"Status: {result['status']}"
        )

    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return TRADE_AMOUNT
    except Exception as e:
        await update.message.reply_text(f"Error executing trade: {str(e)}")
    
    return ConversationHandler.END

async def cancel_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Trade cancelled.")
    return ConversationHandler.END
