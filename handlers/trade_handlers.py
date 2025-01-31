import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from gate_script import buy_spot, sell_spot, get_spot_holdings, check_ticker_exists
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
        logger.info(f"Received sell callback with data: {query.data}")  # Add debug logging
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
            [
                InlineKeyboardButton("Enter coin amount", callback_data=f"sellamt_{coin}"),
                InlineKeyboardButton("Enter USDT amount", callback_data=f"sellusdt_{coin}")
            ]
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
        if update.callback_query:
            await update.callback_query.edit_message_text(f"Error starting sell: {str(e)}")
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

async def handle_sell_usdt_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    try:
        _, coin = extract_coin_from_callback(query.data).split('usdt_')
        context.user_data['trade_coin'] = coin
        context.user_data['sell_by_usdt'] = True
        
        await query.edit_message_text(
            f"How much USDT worth of {coin} would you like to sell?\n"
            "Please enter the USDT amount or /cancel to abort."
        )
        return TRADE_AMOUNT
    except Exception as e:
        logger.error(f"Error in handle_sell_usdt_option: {str(e)}")
        await query.edit_message_text(f"Error setting up sell amount: {str(e)}")
        return ConversationHandler.END

async def start_buy_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the buying process by asking for the coin"""
    context.user_data['awaiting_custom_coin'] = True
    await update.message.reply_text(
        "Please enter the coin symbol you want to buy (e.g., BTC, ETH):"
    )
    return TRADE_AMOUNT

async def execute_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        text = update.message.text
        
        # Handle custom coin input
        if context.user_data.get('awaiting_custom_coin'):
            coin = text.strip().upper()
            context.user_data['trade_coin'] = coin
            context.user_data['trade_type'] = 'buy'
            context.user_data['awaiting_custom_coin'] = False
            
            selected_api = await get_selected_api(update.effective_user.id)
            if not selected_api:
                await update.message.reply_text("Please select an API first using 🔐 My APIs")
                return ConversationHandler.END
            
            if not check_ticker_exists(selected_api['api_key'], selected_api['api_secret'], coin):
                await update.message.reply_text(f"Trading pair {coin}_USDT does not exist.")
                return ConversationHandler.END
            
            await update.message.reply_text(
                f"How many {coin} would you like to buy?\n"
                "Please enter the amount in USDT or /cancel to abort."
            )
            return TRADE_AMOUNT
            
        # Handle amount input
        amount = float(text)
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
            
        # Rest of the existing execute_trade code
        coin = context.user_data['trade_coin']
        trade_type = context.user_data['trade_type']
        
        selected_api = await get_selected_api(update.effective_user.id)
        if not selected_api:
            await update.message.reply_text("Please select an API first using 🔐 My APIs")
            return ConversationHandler.END

        # Handle USDT-based selling
        if trade_type == 'sell' and context.user_data.get('sell_by_usdt'):
            # Get current price to convert USDT amount to coin amount
            spot_holdings = get_spot_holdings(
                api_key=selected_api['api_key'],
                api_secret=selected_api['api_secret']
            )
            
            # Find current price and balance
            coin_price = None
            coin_balance = 0
            for account in spot_holdings.values():
                for holding in account['holdings']:
                    if holding['currency'] == coin:
                        coin_price = holding['price_usdt']
                        coin_balance = holding['total']
                        break
            
            if not coin_price:
                await update.message.reply_text(f"Could not get current price for {coin}")
                return ConversationHandler.END
                
            # Convert USDT amount to coin amount
            coin_amount = amount / coin_price
            
            # Check if user has enough balance
            if coin_amount > coin_balance:
                await update.message.reply_text(
                    f"Insufficient balance. You have {coin_balance:.8f} {coin}\n"
                    f"Required for {amount} USDT: {coin_amount:.8f} {coin}"
                )
                return ConversationHandler.END
                
            amount = coin_amount  # Use converted amount for the sell order

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

        # Show appropriate success message
        if trade_type == 'sell' and context.user_data.get('sell_by_usdt'):
            await update.message.reply_text(
                f"Sell order executed successfully!\n"
                f"Amount: {amount:.8f} {coin} (≈{text} USDT)\n"
                f"Order ID: {result['order_id']}\n"
                f"Status: {result['status']}"
            )
        else:
            await update.message.reply_text(
                f"{trade_type.title()} order executed successfully!\n"
                f"Amount: {amount} {'USDT' if trade_type == 'buy' else coin}\n"
                f"Order ID: {result['order_id']}\n"
                f"Status: {result['status']}"
            )
        
    except ValueError as e:
        await update.message.reply_text(f"Invalid input: {str(e)}")
        return TRADE_AMOUNT
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")
        return ConversationHandler.END
    
    # Clear sell_by_usdt flag
    if 'sell_by_usdt' in context.user_data:
        del context.user_data['sell_by_usdt']
    
    return ConversationHandler.END

async def cancel_trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Trade cancelled.")
    return ConversationHandler.END
    return ConversationHandler.END

