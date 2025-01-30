import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from db_utils import (add_api_key, get_user_api_keys, delete_api_key, 
                     set_selected_api, get_selected_api)
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# States for API conversation
APIKEY, APISECRET, APINAME = range(3)

async def add_api_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please send your Gate.io API key:")
    return APIKEY

async def add_api_key_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['api_key'] = update.message.text
    await update.message.reply_text("Now send your API secret:")
    return APISECRET

async def add_api_secret_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['api_secret'] = update.message.text
    await update.message.reply_text("Give a name for this API (e.g., 'Main Account'):")
    return APINAME

async def add_api_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if await add_api_key(
        update.effective_user.id,
        update.message.text,
        context.user_data['api_key'],
        context.user_data['api_secret']
    ):
        await update.message.reply_text("API keys added successfully!")
    else:
        await update.message.reply_text("Error adding API keys. Please try again.")
    return ConversationHandler.END

async def show_my_apis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        apis = await get_user_api_keys(update.effective_user.id)
        if not apis:
            await update.message.reply_text("You haven't added any API keys yet.\nUse /addapi to add one.")
            return
        
        keyboard = []
        for api in apis:
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑️ Delete {api['name']}", 
                    callback_data=f"delete_api_{api['name']}"
                )
            ])
            keyboard.append([
                InlineKeyboardButton(
                    f"📌 Select {api['name']}", 
                    callback_data=f"select_api_{api['name']}"
                )
            ])
        
        message = "Your API Keys:\n\n"
        for i, api in enumerate(apis, 1):
            message += f"{i}. {api['name']}\n"
            message += f"   Added: {api['added_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
        
        selected_api = await get_selected_api(update.effective_user.id)
        if (selected_api):
            message += f"\nCurrently using: {selected_api['name']}"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error showing APIs: {e}")
        await update.message.reply_text("Error fetching your API keys.")

async def handle_api_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    api_name = query.data.replace("delete_api_", "")
    if await delete_api_key(query.from_user.id, api_name):
        await query.edit_message_text(f"Successfully deleted API key: {api_name}")
    else:
        await query.edit_message_text(f"Failed to delete API key: {api_name}")

async def handle_api_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    api_name = query.data.replace("select_api_", "")
    if await set_selected_api(query.from_user.id, api_name):
        await query.edit_message_text(f"Successfully selected API: {api_name}")
    else:
        await query.edit_message_text(f"Failed to select API: {api_name}")
