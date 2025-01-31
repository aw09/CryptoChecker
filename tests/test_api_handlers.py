import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
from handlers.api_handlers import (
    add_api_start, add_api_key_received, add_api_secret_received,
    add_api_name_received, show_my_apis, show_api_detail,
    handle_api_deletion, handle_api_selection, APIKEY, APISECRET, APINAME
)

@pytest.fixture
def update():
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.message = AsyncMock()
    update.callback_query = AsyncMock()
    return update

@pytest.fixture
def context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    return context

@pytest.mark.asyncio
async def test_add_api_start(update, context):
    result = await add_api_start(update, context)
    
    update.message.reply_text.assert_called_once_with("Please send your Gate.io API key:")
    assert result == APIKEY

@pytest.mark.asyncio
async def test_add_api_key_received(update, context):
    update.message.text = "test_api_key"
    
    result = await add_api_key_received(update, context)
    
    assert context.user_data['api_key'] == "test_api_key"
    update.message.reply_text.assert_called_once_with("Now send your API secret:")
    assert result == APISECRET

@pytest.mark.asyncio
async def test_add_api_secret_received(update, context):
    update.message.text = "test_api_secret"
    
    result = await add_api_secret_received(update, context)
    
    assert context.user_data['api_secret'] == "test_api_secret"
    update.message.reply_text.assert_called_once_with("Give a name for this API (e.g., 'Main Account'):")
    assert result == APINAME

@pytest.mark.asyncio
async def test_add_api_name_received_success():
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.message = AsyncMock()
    update.message.text = "Test API"
    
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {
        'api_key': 'test_key',
        'api_secret': 'test_secret'
    }
    
    with patch('handlers.api_handlers.add_api_key', new_callable=AsyncMock) as mock_add_api:
        mock_add_api.return_value = True
        result = await add_api_name_received(update, context)
        
        mock_add_api.assert_called_once_with(12345, "Test API", "test_key", "test_secret")
        update.message.reply_text.assert_called_once_with("API keys added successfully!")
        assert result == ConversationHandler.END

@pytest.mark.asyncio
async def test_handle_api_deletion_success(update, context):
    update.callback_query.data = "delete_api_Test API"
    
    with patch('handlers.api_handlers.delete_api_key', new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = True
        
        await handle_api_deletion(update, context)
        
        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once_with(
            "Successfully deleted API key: Test API"
        )

@pytest.mark.asyncio
async def test_handle_api_selection_success(update, context):
    update.callback_query.data = "select_api_Test API"
    
    with patch('handlers.api_handlers.set_selected_api', new_callable=AsyncMock) as mock_set:
        mock_set.return_value = True
        
        await handle_api_selection(update, context)
        
        update.callback_query.answer.assert_called_once()
        update.callback_query.edit_message_text.assert_called_once_with(
            "Successfully selected API: Test API"
        )

@pytest.mark.asyncio
async def test_show_my_apis_direct_message(update, context):
    """Test showing APIs through direct message"""
    mock_apis = [
        {
            'name': 'Test API 1',
            'added_at': datetime.now(),
        },
        {
            'name': 'Test API 2',
            'added_at': datetime.now(),
        }
    ]
    
    # Set callback_query to None for direct message testing
    update.callback_query = None
    
    with patch('handlers.api_handlers.get_user_api_keys', new_callable=AsyncMock) as mock_get_apis, \
         patch('handlers.api_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_selected:
        mock_get_apis.return_value = mock_apis
        mock_get_selected.return_value = {'name': 'Test API 1'}
        
        await show_my_apis(update, context)
        
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert isinstance(call_args[1]['reply_markup'], InlineKeyboardMarkup)
        assert "Test API 1" in call_args[1]['text']
        assert "Test API 2" in call_args[1]['text']
        assert "Currently using: Test API 1" in call_args[1]['text']

@pytest.mark.asyncio
async def test_show_my_apis_callback_query(update, context):
    """Test showing APIs through callback query"""
    mock_apis = [
        {
            'name': 'Test API 1',
            'added_at': datetime.now(),
        },
        {
            'name': 'Test API 2',
            'added_at': datetime.now(),
        }
    ]
    
    with patch('handlers.api_handlers.get_user_api_keys', new_callable=AsyncMock) as mock_get_apis, \
         patch('handlers.api_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_selected:
        mock_get_apis.return_value = mock_apis
        mock_get_selected.return_value = {'name': 'Test API 1'}
        
        await show_my_apis(update, context)
        
        update.callback_query.edit_message_text.assert_called_once()
        call_args = update.callback_query.edit_message_text.call_args
        assert isinstance(call_args[1]['reply_markup'], InlineKeyboardMarkup)
        assert "Test API 1" in call_args[1]['text']
        assert "Test API 2" in call_args[1]['text']
        assert "Currently using: Test API 1" in call_args[1]['text']

@pytest.mark.asyncio
async def test_show_my_apis_no_apis_direct_message(update, context):
    """Test showing no APIs through direct message"""
    update.callback_query = None
    
    with patch('handlers.api_handlers.get_user_api_keys', new_callable=AsyncMock) as mock_get_apis:
        mock_get_apis.return_value = []
        
        await show_my_apis(update, context)
        
        update.message.reply_text.assert_called_once_with(
            "You haven't added any API keys yet.\nUse /addapi to add one."
        )

@pytest.mark.asyncio
async def test_show_my_apis_no_apis_callback_query(update, context):
    """Test showing no APIs through callback query"""
    with patch('handlers.api_handlers.get_user_api_keys', new_callable=AsyncMock) as mock_get_apis:
        mock_get_apis.return_value = []
        
        await show_my_apis(update, context)
        
        update.callback_query.edit_message_text.assert_called_once_with(
            "You haven't added any API keys yet.\nUse /addapi to add one."
        )
