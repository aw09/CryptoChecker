import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from gate_script import get_balance, get_spot_holdings
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

    try:
        selected_api = await get_selected_api(update.effective_user.id)
        print(f"Selected API: {selected_api['name'] if selected_api else 'None'}")
        
        if not selected_api:
            await update.message.reply_text("Please select an API first using 🔐 My APIs")
            return

        processing_msg = await update.message.reply_text("Processing...")
        
        print(f"Getting balance for API: {selected_api['name']}")
        balances = get_balance(api_key=selected_api['api_key'], 
                             api_secret=selected_api['api_secret'])
        total = balances.pop('total')
        
        message_parts = [f"{datetime.now()}\n"]
        for account, data in balances.items():
            message_parts.append(f"=== {data['name']} ===\n"
                               f"Total Asset in USDT: {format(data['balance'], ',.2f')}\n")
        
        message_parts.append(f"\n=== TOTAL ===\n"
                           f"Total Asset in USDT: {format(total, ',.2f')}")
        
        await update.message.reply_text('\n'.join(message_parts))
        await processing_msg.delete()
        
    except Exception as e:
        await update.message.reply_text(f"Error getting balances: {str(e)}")

async def sendHoldings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Received holdings command from {update.effective_user.username}")

    try:
        selected_api = await get_selected_api(update.effective_user.id)
        if not selected_api:
            await update.message.reply_text("Please select an API first using 🔐 My APIs")
            return

        processing_msg = await update.message.reply_text("Processing...")
        all_holdings = get_spot_holdings(api_key=selected_api['api_key'],
                                       api_secret=selected_api['api_secret'],
                                       min_usdt_value=0.5)
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
        
        grand_total = sum(account_total_usdt.values())
        message_parts.append(f"\n=== GRAND TOTAL ===\n{format(grand_total, '.2f')} USDT")
        
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
