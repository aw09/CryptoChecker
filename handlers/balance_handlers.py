import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from gate_script import get_balance, get_spot_holdings, get_earn_balances
from db_utils import get_selected_api
import textwrap

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

        if total_value > 0:
            message_parts.append(f"\n\nTotal Earn Value: {format(total_value, ',.2f')} USDT")  # Added comma formatting

        keyboard = [[
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_earn")
        ]]
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
    await sendEarn(update, context)
