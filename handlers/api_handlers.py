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
        
        selected_api = await get_selected_api(update.effective_user.id)
        keyboard = []
        
        for api in apis:
            keyboard.append([
                InlineKeyboardButton(
                    f"📋 Details for {api['name']}", 
                    callback_data=f"api_detail_{api['name']}"
                )
            ])
            # Only show select button if the API is not currently selected
            if not selected_api or selected_api['name'] != api['name']:
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
        
        if selected_api:
            message += f"\nCurrently using: {selected_api['name']}"
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error showing APIs: {e}")
        await update.message.reply_text("Error fetching your API keys.")

async def show_api_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show API details and delete option"""
    query = update.callback_query
    await query.answer()
    
    api_name = query.data.replace("api_detail_", "")
    apis = await get_user_api_keys(query.from_user.id)
    api = next((a for a in apis if a['name'] == api_name), None)
    
    if not api:
        await query.edit_message_text("API not found.")
        return
    
    message = f"API Details for {api['name']}\n"
    message += f"Added: {api['added_at'].strftime('%Y-%m-%d %H:%M')}\n"
    message += "\n⚠️ Deleting an API is irreversible!"
    
    keyboard = [[
        InlineKeyboardButton("🗑️ Delete API", callback_data=f"delete_api_{api_name}")
    ], [
        InlineKeyboardButton("« Back to API List", callback_data="back_to_apis")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup)

async def back_to_apis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle back button to API list"""
    query = update.callback_query
    await query.answer()
    await show_my_apis(update, context)

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
