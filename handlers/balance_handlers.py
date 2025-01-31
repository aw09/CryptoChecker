import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from gate_script import get_balance, get_spot_holdings, get_earn_balances, redeem_from_earn, get_lending_rates, lend_to_earn
from db_utils import get_selected_api
import textwrap

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def format_number(value):
    """Format number with appropriate decimal places based on magnitude"""
    if isinstance(value, str):
        value = float(value)
    if value >= 1000:
        return f"{value:,.2f}"  # Use comma as thousand separator and 2 decimal places
    elif value >= 1:
        return f"{value:.4f}"   # 4 decimal places for values between 1 and 1000
    else:
        return f"{value:.8f}"   # 8 decimal places for values less than 1

async def sendInfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Received command from {update.effective_user.username}")
    is_callback = bool(update.callback_query)
    
    try:
        selected_api = await get_selected_api(update.effective_user.id)
        print(f"Selected API: {selected_api['name'] if selected_api else 'None'}")
        
        if not selected_api:
            message = "Please select an API first using 🔐 My APIs"
            if is_callback:
                await update.callback_query.edit_message_text(message)
            else:
                await update.message.reply_text(message)
            return

        processing_msg = None if is_callback else await update.message.reply_text("Processing...")
        
        print(f"Getting balance for API: {selected_api['name']}")
        balances = get_balance(api_key=selected_api['api_key'], 
                             api_secret=selected_api['api_secret'])
        total = balances.pop('total')
        
        message_parts = [
            f"🔑 Using API: {selected_api['name']}\n",
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        ]
        
        for account, data in balances.items():
            message_parts.append(f"=== {data['name']} ===\n"
                               f"Total Asset in USDT: {format(data['balance'], ',.2f')}\n")
        
        message_parts.append(f"\n=== TOTAL ===\n"
                           f"Total Asset in USDT: {format(total, ',.2f')}")
        
        keyboard = [[
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_balance")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message_text = '\n'.join(message_parts)
        
        if is_callback:
            await update.callback_query.edit_message_text(
                text=message_text,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=message_text,
                reply_markup=reply_markup
            )
            if processing_msg:
                await processing_msg.delete()
        
    except Exception as e:
        error_message = f"Error getting balances: {str(e)}"
        if is_callback:
            await update.callback_query.edit_message_text(error_message)
        else:
            await update.message.reply_text(error_message)

async def sendHoldings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Received holdings command from {update.effective_user.username}")
    is_callback = bool(update.callback_query)

    try:
        selected_api = await get_selected_api(update.effective_user.id)
        if not selected_api:
            message = "Please select an API first using 🔐 My APIs"
            if is_callback:
                await update.callback_query.edit_message_text(message)
            else:
                await update.message.reply_text(message)
            return

        processing_msg = None if is_callback else await update.message.reply_text("Processing...")
        all_holdings = get_spot_holdings(api_key=selected_api['api_key'],
                                       api_secret=selected_api['api_secret'],
                                       min_usdt_value=0.5)
        
        message_parts = [
            f"🔑 Using API: {selected_api['name']}\n",
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        ]
        
        account_total_usdt = {}
        keyboard = []
        
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
                # Only add buy/sell buttons for non-USDT holdings
                if holding['currency'] != 'USDT':
                    keyboard.append([
                        InlineKeyboardButton(f"Buy {holding['currency']}", callback_data=f"buy_{holding['currency']}"),
                        InlineKeyboardButton(f"Sell {holding['currency']}", callback_data=f"sell_{holding['currency']}")
                    ])
            
            account_total_usdt[account_name] = account_total
            message_parts.append(f"\nSubtotal: {format(account_total, '.2f')} USDT")
        
        grand_total = sum(account_total_usdt.values())
        message_parts.append(f"\n=== GRAND TOTAL ===\n{format(grand_total, '.2f')} USDT")
        
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_holdings")
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        full_message = '\n'.join(message_parts)
        if len(full_message) > 4000:
            if is_callback:
                await update.callback_query.edit_message_text(
                    "Message too long for callback query. Please use the menu command again."
                )
            else:
                chunks = textwrap.wrap(full_message, 4000)
                for i, chunk in enumerate(chunks):
                    if i == len(chunks) - 1:
                        await update.message.reply_text(chunk, reply_markup=reply_markup)
                    else:
                        await update.message.reply_text(chunk)
        else:
            if is_callback:
                await update.callback_query.edit_message_text(
                    text=full_message,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    text=full_message,
                    reply_markup=reply_markup
                )
        
        if processing_msg:
            await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"Error getting holdings: {str(e)}")
        error_message = f"Error getting holdings: {str(e)}"
        if is_callback:
            await update.callback_query.edit_message_text(error_message)
        else:
            await update.message.reply_text(error_message)

async def refresh_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await sendInfo(update, context)

async def refresh_holdings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await sendHoldings(update, context)

async def sendEarn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Received earn command from {update.effective_user.username}")
    is_callback = bool(update.callback_query)

    try:
        selected_api = await get_selected_api(update.effective_user.id)
        if not selected_api:
            message = "Please select an API first using 🔐 My APIs"
            if is_callback:
                await update.callback_query.edit_message_text(message)
            else:
                await update.message.reply_text(message)
            return

        processing_msg = None if is_callback else await update.message.reply_text("Processing...")
        
        earn_balances = get_earn_balances(api_key=selected_api['api_key'],
                                        api_secret=selected_api['api_secret'])

        message_parts = [
            f"🔑 Using API: {selected_api['name']}\n",
            f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        ]

        total_value = 0
        keyboard = []  # Initialize keyboard list here
        
        for account_name, data in earn_balances.items():
            if not data['holdings']:
                message_parts.append("\nNo active earn positions found.")
                continue

            for holding in data['holdings']:
                total_value += holding['value_usdt']
                message_parts.append(
                    f"\n{holding['currency']}:"
                    f"\n  Amount: {format(holding['amount'], '.8f')}"
                    f"\n  APR: {format(holding['min_rate'] * 100, '.2f')}%"
                    f"\n  Value: {format(holding['value_usdt'], ',.2f')} USDT"  # Added comma formatting
                )
                # Add redeem and lend buttons for each currency
                keyboard.append([
                    InlineKeyboardButton(f"Redeem {holding['currency']}", callback_data=f"redeem_{holding['currency']}"),
                    InlineKeyboardButton(f"Lend {holding['currency']}", callback_data=f"lend_{holding['currency']}")
                ])

        if total_value > 0:
            message_parts.append(f"\n\nTotal Earn Value: {format(total_value, ',.2f')} USDT")  # Added comma formatting

        # Add refresh button at the bottom
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_earn")
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        full_message = '\n'.join(message_parts)
        if len(full_message) > 4000:
            if is_callback:
                await update.callback_query.edit_message_text(
                    "Message too long for callback query. Please use the menu command again."
                )
            else:
                chunks = textwrap.wrap(full_message, 4000)
                for i, chunk in enumerate(chunks):
                    if i == len(chunks) - 1:
                        await update.message.reply_text(chunk, reply_markup=reply_markup)
                    else:
                        await update.message.reply_text(chunk)
        else:
            if is_callback:
                await update.callback_query.edit_message_text(
                    text=full_message,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    text=full_message,
                    reply_markup=reply_markup
                )

        if processing_msg:
            await processing_msg.delete()

    except Exception as e:
        logger.error(f"Error getting earn positions: {str(e)}")
        error_message = f"Error getting earn positions: {str(e)}"
        if is_callback:
            await update.callback_query.edit_message_text(error_message)
        else:
            await update.message.reply_text(error_message)

async def refresh_earn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    try:
        api_data = get_selected_api()
        if not api_data:
            await query.edit_message_text("No API selected. Please select an API first.")
            return

        earn_data = get_earn_balances(api_data['api_key'], api_data['api_secret'])
        
        message = "*Earn Products:*\n\n"
        keyboard = []
        
        if earn_data and earn_data['account1']['holdings']:
            for holding in earn_data['account1']['holdings']:
                currency = holding['currency']
                amount = format_number(holding['amount'])
                value_usdt = format_number(holding['value_usdt'])
                min_rate = format_number(holding['min_rate'] * 100)
                
                message += f"*{currency}*\n"
                message += f"Amount: {amount}\n"
                message += f"Value: ${value_usdt}\n"
                message += f"APR: {min_rate}%\n\n"
                
                # Add redeem and lend buttons for each currency
                keyboard.append([
                    InlineKeyboardButton(f"Redeem {currency}", callback_data=f"redeem_{currency}"),
                    InlineKeyboardButton(f"Lend {currency}", callback_data=f"lend_{currency}")
                ])
        else:
            message += "No assets in earn products.\n"
        
        # Add refresh button at the bottom
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_earn")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await query.edit_message_text(f"Error refreshing earn data: {str(e)}")

async def handle_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle redeem from earn callback"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Extract currency from callback data (format: "redeem_BTC")
        currency = query.data.split('_')[1]
        api_data = get_selected_api()
        
        if not api_data:
            await query.edit_message_text("No API selected. Please select an API first.")
            return
            
        # Redeem all available amount for the currency
        result = redeem_from_earn(
            api_data['api_key'], 
            api_data['api_secret'],
            currency,
            redeem_all=True
        )
        
        if result['status'] == 'success':
            await query.edit_message_text(
                f"Successfully redeemed {currency} from earn.\nPlease wait a few minutes for the transaction to process.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh Earn", callback_data="refresh_earn")]
                ])
            )
        else:
            await query.edit_message_text(
                f"Failed to redeem {currency} from earn: {result.get('error', 'Unknown error')}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh Earn", callback_data="refresh_earn")]
                ])
            )
            
    except Exception as e:
        await query.edit_message_text(
            f"Error processing redeem: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh Earn", callback_data="refresh_earn")]
            ])
        )

async def handle_lend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle lending to earn"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Extract currency from callback data (format: "lend_BTC")
        currency = query.data.split('_')[1]
        api_data = get_selected_api()
        
        if not api_data:
            await query.edit_message_text("No API selected. Please select an API first.")
            return
        
        # Get available balance for the currency
        holdings = get_spot_holdings(api_data['api_key'], api_data['api_secret'])
        available_amount = 0
        
        for holding in holdings['account1']['holdings']:
            if holding['currency'] == currency:
                available_amount = holding['available']
                break
        
        if available_amount <= 0:
            await query.edit_message_text(
                f"No available {currency} balance to lend.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh Earn", callback_data="refresh_earn")]
                ])
            )
            return
            
        # Get lending rates
        rates = get_lending_rates(api_data['api_key'], api_data['api_secret'])
        if currency not in rates:
            await query.edit_message_text(
                f"{currency} is not available for lending.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh Earn", callback_data="refresh_earn")]
                ])
            )
            return
        
        # Lend all available amount at minimum rate
        result = lend_to_earn(
            api_data['api_key'],
            api_data['api_secret'],
            currency,
            available_amount,
            rates[currency]['min_rate']
        )
        
        if result['status'] == 'success':
            await query.edit_message_text(
                f"Successfully lent {format_number(available_amount)} {currency} to earn at {format_number(result['min_rate']*100)}% APR",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh Earn", callback_data="refresh_earn")]
                ])
            )
        else:
            await query.edit_message_text(
                f"Failed to lend {currency}: {result.get('error', 'Unknown error')}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Refresh Earn", callback_data="refresh_earn")]
                ])
            )
            
    except Exception as e:
        await query.edit_message_text(
            f"Error processing lend: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh Earn", callback_data="refresh_earn")]
            ])
        )
