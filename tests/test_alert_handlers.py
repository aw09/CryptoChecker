import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, Chat, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from handlers.alert_handlers import (
    add_alert_start, alert_coin_received, alert_condition_received,
    alert_price_received, cancel_alert, check_alerts,
    ALERT_COIN, ALERT_CONDITION, ALERT_PRICE
)
import asyncio

@pytest.fixture
def update():
    update = AsyncMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456789
    update.effective_user.username = "testuser"
    update.message = AsyncMock(spec=Message)
    update.message.chat = MagicMock(spec=Chat)
    update.message.chat.id = 123456789
    return update

@pytest.fixture
def context():
    context = AsyncMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    return context

@pytest.mark.asyncio
async def test_add_alert_start(update, context):
    # Test starting the alert conversation
    result = await add_alert_start(update, context)
    
    update.message.reply_text.assert_called_once_with(
        "Which coin do you want to track? (e.g., BTC)"
    )
    assert result == ALERT_COIN

@pytest.mark.asyncio
async def test_alert_coin_received_valid(update, context):
    # Mock the API selection and ticker check
    with patch('handlers.alert_handlers.get_selected_api') as mock_get_api, \
         patch('handlers.alert_handlers.check_ticker_exists') as mock_check_ticker, \
         patch('handlers.alert_handlers.check_current_price') as mock_current_price:
        
        mock_get_api.return_value = {'api_key': 'test', 'api_secret': 'test'}
        mock_check_ticker.return_value = True
        mock_current_price.return_value = 50000
        
        update.message.text = "BTC"
        
        result = await alert_coin_received(update, context)
        
        assert result == ALERT_CONDITION
        assert context.user_data['coin'] == "BTC"
        assert isinstance(update.message.reply_text.call_args[1]['reply_markup'], InlineKeyboardMarkup)

@pytest.mark.asyncio
async def test_alert_coin_received_invalid_api(update, context):
    # Test when no API is selected
    with patch('handlers.alert_handlers.get_selected_api') as mock_get_api:
        mock_get_api.return_value = None
        
        update.message.text = "BTC"
        
        result = await alert_coin_received(update, context)
        
        assert result == ConversationHandler.END
        update.message.reply_text.assert_called_once_with(
            "Please select an API first using 🔐 My APIs"
        )

@pytest.mark.asyncio
async def test_alert_price_received_valid(update, context):
    context.user_data = {
        'coin': 'BTC',
        'condition': '>'
    }
    update.message.text = "50000"
    
    with patch('handlers.alert_handlers.set_alert') as mock_set_alert:
        mock_set_alert.return_value = True
        
        result = await alert_price_received(update, context)
        
        assert result == ConversationHandler.END
        update.message.reply_text.assert_called_once_with("Alert set successfully!")

@pytest.mark.asyncio
async def test_alert_price_received_invalid(update, context):
    update.message.text = "invalid_price"
    
    result = await alert_price_received(update, context)
    
    assert result == ALERT_PRICE
    update.message.reply_text.assert_called_once_with("Please enter a valid number")

@pytest.mark.asyncio
async def test_check_alerts(update):
    bot = AsyncMock()
    
    with patch('handlers.alert_handlers.get_user_alerts') as mock_get_alerts, \
         patch('handlers.alert_handlers.get_selected_api') as mock_get_api, \
         patch('handlers.alert_handlers.get_multiple_prices') as mock_get_prices, \
         patch('handlers.alert_handlers.pymongo.MongoClient'):
        
        # Mock alert data
        mock_get_alerts.return_value = [{
            '_id': '123',
            'user_id': 123456789,
            'coin': 'BTC',
            'condition': '>',
            'price': 50000,
            'active': True
        }]
        
        mock_get_api.return_value = {'api_key': 'test', 'api_secret': 'test'}
        mock_get_prices.return_value = {'BTC': 51000}
        
        # Run check_alerts for one iteration
        check_task = check_alerts(bot)
        try:
            await asyncio.wait_for(check_task, timeout=1)
        except asyncio.TimeoutError:
            pass  # Expected timeout as check_alerts runs indefinitely
        
        # Verify alert was triggered
        bot.send_message.assert_called_once()
        assert "Alert Triggered!" in bot.send_message.call_args[1]['text']
