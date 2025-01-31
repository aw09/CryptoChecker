import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from gate_script import buy_spot, sell_spot, get_spot_holdings, check_ticker_exists, get_earn_balances, redeem_from_earn
from db_utils import get_selected_api
import asyncio

# Add new state for percentage selection
TRADE_AMOUNT, TRADE_PERCENTAGE = range(2)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_coin_from_callback(callback_data: str) -> str:
    """Extract coin name from callback data, handling USDT pairs"""
    try:
        parts = callback_data.split('_')
        logger.info(f"Callback data parts: {parts}")  # Debug logging
        
        # Handle sellusdt pattern
        if parts[0] == 'sellusdt':
            return parts[1]
            
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
    except Exception as e:
        logger.error(f"Error parsing callback data '{callback_data}': {str(e)}")
        raise

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
        
        # Get current holdings and price
        selected_api = await get_selected_api(update.effective_user.id)
        if not selected_api:
            await query.edit_message_text("Please select an API first using 🔐 My APIs")
            return ConversationHandler.END
            
        holdings = get_spot_holdings(
            api_key=selected_api['api_key'],
            api_secret=selected_api['api_secret']
        )
        
        # Find coin balance and price
        coin_balance = 0
        coin_price = 0
        for account in holdings.values():
            for holding in account['holdings']:
                if holding['currency'] == coin:
                    coin_balance = holding['total']
                    coin_price = holding['price_usdt']
                    break
        
        usdt_value = coin_balance * coin_price
        
        await query.edit_message_text(
            f"You have {coin_balance:.8f} {coin}\n"
            f"≈ {usdt_value:.2f} USDT\n\n"
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
        coin = extract_coin_from_callback(query.data)
        logger.info(f"Handling USDT sell for coin: {coin}")  # Debug logging
        
        context.user_data['trade_coin'] = coin
        context.user_data['sell_by_usdt'] = True
        
        # Get current holdings and price
        selected_api = await get_selected_api(update.effective_user.id)
        if not selected_api:
            await query.edit_message_text("Please select an API first using 🔐 My APIs")
            return ConversationHandler.END
            
        holdings = get_spot_holdings(
            api_key=selected_api['api_key'],
            api_secret=selected_api['api_secret']
        )
        
        # Find coin balance and price
        coin_balance = 0
        coin_price = 0
        for account in holdings.values():
            for holding in account['holdings']:
                if holding['currency'] == coin:
                    coin_balance = holding['total']
                    coin_price = holding['price_usdt']
                    break
        
        usdt_value = coin_balance * coin_price
        
        await query.edit_message_text(
            f"You have {coin_balance:.8f} {coin}\n"
            f"≈ {usdt_value:.2f} USDT\n\n"
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
            
            # Check if the trading pair exists
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

async def handle_sell_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle selling all assets"""
    try:
        # Show confirmation button first
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm SELL ALL", callback_data="confirm_sell_all"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_sell_all")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ WARNING: This will sell ALL your assets to USDT!\n\n"
            "1. Redeem all from earn products\n"
            "2. Sell all holdings at market price\n\n"
            "Are you sure?",
            reply_markup=reply_markup
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def execute_sell_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute the sell all operation"""
    query = update.callback_query
    await query.answer()
    
    try:
        api_data = await get_selected_api(update.effective_user.id)
        if not api_data:
            await query.edit_message_text("No API selected. Please select an API first.")
            return

        status_message = await query.edit_message_text("Starting sell all process...")
        results = []

        # Step 1: Redeem all from earn
        try:
            earn_data = get_earn_balances(api_data['api_key'], api_data['api_secret'])
            if earn_data and earn_data['account1']['holdings']:
                for holding in earn_data['account1']['holdings']:
                    currency = holding['currency']
                    try:
                        result = redeem_from_earn(
                            api_data['api_key'],
                            api_data['api_secret'],
                            currency,
                            redeem_all=True
                        )
                        results.append(f"✅ Redeemed {currency} from earn")
                    except Exception as e:
                        results.append(f"❌ Failed to redeem {currency}: {str(e)}")
                
                # Wait message for earn redemption
                results.append("⏳ Waiting for earn redemptions to process (30 seconds)...")
                await status_message.edit_text("\n".join(results))
                await asyncio.sleep(30)  # Wait 30 seconds for earn redemptions to process
        except Exception as e:
            results.append(f"❌ Error checking earn positions: {str(e)}")

        # Step 2: Sell all holdings
        try:
            holdings = get_spot_holdings(api_data['api_key'], api_data['api_secret'])
            if holdings and holdings['account1']['holdings']:
                for holding in holdings['account1']['holdings']:
                    currency = holding['currency']
                    available = holding['available']
                    
                    if currency != 'USDT' and available > 0:
                        try:
                            result = sell_spot(
                                api_data['api_key'],
                                api_data['api_secret'],
                                currency,
                                available
                            )
                            results.append(f"✅ Sold {available} {currency}")
                        except Exception as e:
                            results.append(f"❌ Failed to sell {currency}: {str(e)}")
        except Exception as e:
            results.append(f"❌ Error selling holdings: {str(e)}")

        # Final status update
        results.append("\n🏁 Sell all process completed!")
        await status_message.edit_text(
            "\n".join(results),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Check Holdings", callback_data="refresh_holdings")]
            ])
        )

    except Exception as e:
        await query.edit_message_text(f"Error executing sell all: {str(e)}")

async def cancel_sell_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel sell all operation"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Sell all operation cancelled.")

