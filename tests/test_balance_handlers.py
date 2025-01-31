import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
from handlers.balance_handlers import (
    sendInfo, sendHoldings, sendEarn,
    refresh_balance, refresh_holdings, refresh_earn
)

@pytest.fixture
def update():
    update = MagicMock(spec=Update)
    update.effective_user.id = 12345
    update.effective_user.username = "testuser"
    update.message = AsyncMock()
    update.callback_query = AsyncMock()
    return update

@pytest.fixture
def context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    return context

@pytest.fixture
def mock_selected_api():
    return {
        'name': 'Test API',
        'api_key': 'test_key',
        'api_secret': 'test_secret'
    }

@pytest.fixture
def mock_balance_data():
    return {
        'spot': {'name': 'Spot Account', 'balance': 1000.0},
        'margin': {'name': 'Margin Account', 'balance': 500.0},
        'total': 1500.0
    }

@pytest.fixture
def mock_holdings_data():
    return {
        'spot': {
            'name': 'Spot Account',
            'holdings': [
                {
                    'currency': 'BTC',
                    'total': 0.5,
                    'price_usdt': 30000.0,
                    'value_usdt': 15000.0
                },
                {
                    'currency': 'ETH',
                    'total': 2.0,
                    'price_usdt': 2000.0,
                    'value_usdt': 4000.0
                }
            ]
        }
    }

@pytest.fixture
def mock_earn_data():
    return {
        'account1': {
            'name': 'Test Account',
            'holdings': [
                {
                    'currency': 'BTC',
                    'amount': 0.1,
                    'min_rate': 0.05,  # 5% APR
                    'value_usdt': 3000.0,
                    'frozen_amount': 0.0,
                    'interest_status': 'active',
                    'create_time': '2023-01-01T00:00:00Z',
                    'update_time': '2023-01-01T00:00:00Z'
                },
                {
                    'currency': 'USDT',
                    'amount': 1000.0,
                    'min_rate': 0.08,  # 8% APR
                    'value_usdt': 1000.0,
                    'frozen_amount': 0.0,
                    'interest_status': 'active',
                    'create_time': '2023-01-01T00:00:00Z',
                    'update_time': '2023-01-01T00:00:00Z'
                }
            ]
        }
    }

@pytest.mark.asyncio
async def test_send_info_no_selected_api(update, context):
    update.callback_query = None  # Force direct message mode
    with patch('handlers.balance_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_api:
        mock_get_api.return_value = None
        
        await sendInfo(update, context)
        
        update.message.reply_text.assert_called_once_with(
            "Please select an API first using 🔐 My APIs"
        )

@pytest.mark.asyncio
async def test_send_info_direct_message_success(update, context, mock_selected_api, mock_balance_data):
    """Test sendInfo with direct message"""
    update.callback_query = None  # Ensure we're testing direct message
    mock_balance_data['total'] = 1500.0  # Ensure total is present
    
    with patch('handlers.balance_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_api, \
         patch('handlers.balance_handlers.get_balance', return_value=mock_balance_data):
        mock_get_api.return_value = mock_selected_api
        
        await sendInfo(update, context)
        
        # Check call count and processing message
        calls = update.message.reply_text.call_args_list
        assert len(calls) >= 2
        assert calls[0][0][0] == "Processing..."
        
        # Check final message
        final_call = calls[-1]
        kwargs = final_call[1]  # Get kwargs
        message_text = kwargs['text']  # Get text from kwargs
        reply_markup = kwargs['reply_markup']  # Get reply_markup from kwargs
        
        # Check content
        assert "🔑 Using API: Test API" in message_text
        assert "Total Asset in USDT: 1,000.00" in message_text
        assert isinstance(reply_markup, InlineKeyboardMarkup)
        assert reply_markup.inline_keyboard[0][0].callback_data == "refresh_balance"

@pytest.mark.asyncio
async def test_send_info_callback_query_success(update, context, mock_selected_api, mock_balance_data):
    """Test sendInfo with callback query"""
    with patch('handlers.balance_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_api, \
         patch('handlers.balance_handlers.get_balance', return_value=mock_balance_data):
        mock_get_api.return_value = mock_selected_api
        
        await sendInfo(update, context)
        
        # Check final message
        final_call = update.callback_query.edit_message_text.call_args
        message_text = final_call[1]['text']
        reply_markup = final_call[1]['reply_markup']
        
        # Check content
        assert "🔑 Using API: Test API" in message_text
        assert "Total Asset in USDT: 1,000.00" in message_text
        assert "Total Asset in USDT: 1,500.00" in message_text
        assert isinstance(reply_markup, InlineKeyboardMarkup)
        assert reply_markup.inline_keyboard[0][0].callback_data == "refresh_balance"

@pytest.mark.asyncio
async def test_send_holdings_direct_message_success(update, context, mock_selected_api, mock_holdings_data):
    """Test sendHoldings with direct message"""
    update.callback_query = None  # Ensure we're testing direct message
    
    with patch('handlers.balance_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_api, \
         patch('handlers.balance_handlers.get_spot_holdings', return_value=mock_holdings_data):
        mock_get_api.return_value = mock_selected_api
        
        await sendHoldings(update, context)
        
        # Check call count and processing message
        calls = update.message.reply_text.call_args_list
        assert len(calls) >= 2
        assert calls[0][0][0] == "Processing..."
        
        # Check final message
        final_call = calls[-1]
        kwargs = final_call[1]  # Get kwargs
        message_text = kwargs['text']  # Get text from kwargs
        reply_markup = kwargs['reply_markup']  # Get reply_markup from kwargs
        
        # Check content
        assert "🔑 Using API: Test API" in message_text
        assert "BTC" in message_text
        assert isinstance(reply_markup, InlineKeyboardMarkup)
        assert reply_markup.inline_keyboard[0][0].callback_data == "refresh_holdings"

@pytest.mark.asyncio
async def test_send_holdings_callback_query_success(update, context, mock_selected_api, mock_holdings_data):
    """Test sendHoldings with callback query"""
    with patch('handlers.balance_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_api, \
         patch('handlers.balance_handlers.get_spot_holdings', return_value=mock_holdings_data):
        mock_get_api.return_value = mock_selected_api
        
        await sendHoldings(update, context)
        
        # Check final message
        final_call = update.callback_query.edit_message_text.call_args
        message_text = final_call[1]['text']
        reply_markup = final_call[1]['reply_markup']
        
        # Check content
        assert "🔑 Using API: Test API" in message_text
        assert "BTC" in message_text
        assert "Amount: 0.50000000" in message_text
        assert isinstance(reply_markup, InlineKeyboardMarkup)
        assert reply_markup.inline_keyboard[0][0].callback_data == "refresh_holdings"

@pytest.mark.asyncio
async def test_send_info_no_api_direct_message(update, context):
    """Test sendInfo with no API selected - direct message"""
    update.callback_query = None
    with patch('handlers.balance_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_api:
        mock_get_api.return_value = None
        await sendInfo(update, context)
        update.message.reply_text.assert_called_once_with(
            "Please select an API first using 🔐 My APIs"
        )

@pytest.mark.asyncio
async def test_send_info_no_api_callback_query(update, context):
    """Test sendInfo with no API selected - callback query"""
    with patch('handlers.balance_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_api:
        mock_get_api.return_value = None
        await sendInfo(update, context)
        update.callback_query.edit_message_text.assert_called_once_with(
            "Please select an API first using 🔐 My APIs"
        )

@pytest.mark.asyncio
async def test_refresh_balance(update, context):
    with patch('handlers.balance_handlers.sendInfo') as mock_send_info:
        await refresh_balance(update, context)
        
        update.callback_query.answer.assert_called_once()
        mock_send_info.assert_called_once_with(update, context)

@pytest.mark.asyncio
async def test_refresh_holdings(update, context):
    with patch('handlers.balance_handlers.sendHoldings') as mock_send_holdings:
        await refresh_holdings(update, context)
        
        update.callback_query.answer.assert_called_once()
        mock_send_holdings.assert_called_once_with(update, context)

@pytest.mark.asyncio
async def test_send_holdings_with_error(update, context, mock_selected_api):
    """Test error handling in sendHoldings"""
    update.callback_query = None  # Ensure we're testing direct message
    
    with patch('handlers.balance_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_api, \
         patch('handlers.balance_handlers.get_spot_holdings', side_effect=Exception("Test error")):
        mock_get_api.return_value = mock_selected_api
        
        await sendHoldings(update, context)
        
        # Verify error message
        calls = update.message.reply_text.call_args_list
        final_call = calls[-1] if calls else None
        assert final_call is not None
        assert final_call[0][0] == "Error getting holdings: Test error"

@pytest.mark.asyncio
async def test_send_earn_no_selected_api(update, context):
    """Test sendEarn with no API selected"""
    update.callback_query = None  # Force direct message mode
    with patch('handlers.balance_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_api:
        mock_get_api.return_value = None
        
        await sendEarn(update, context)
        
        update.message.reply_text.assert_called_once_with(
            "Please select an API first using 🔐 My APIs"
        )

@pytest.mark.asyncio
async def test_send_earn_direct_message_success(update, context, mock_selected_api, mock_earn_data):
    """Test sendEarn with direct message"""
    update.callback_query = None  # Ensure we're testing direct message
    
    with patch('handlers.balance_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_api, \
         patch('handlers.balance_handlers.get_earn_balances', return_value=mock_earn_data):
        mock_get_api.return_value = mock_selected_api
        
        await sendEarn(update, context)
        
        # Check call count and processing message
        calls = update.message.reply_text.call_args_list
        assert len(calls) >= 2
        assert calls[0][0][0] == "Processing..."
        
        # Check final message
        final_call = calls[-1]
        kwargs = final_call[1]
        message_text = kwargs['text']
        reply_markup = kwargs['reply_markup']
        
        # Check content
        assert "🔑 Using API: Test API" in message_text
        assert "BTC" in message_text
        assert "APR: 5.00%" in message_text
        assert "Total Earn Value: 4,000.00" in message_text
        assert isinstance(reply_markup, InlineKeyboardMarkup)
        assert reply_markup.inline_keyboard[0][0].callback_data == "refresh_earn"

@pytest.mark.asyncio
async def test_send_earn_callback_query_success(update, context, mock_selected_api, mock_earn_data):
    """Test sendEarn with callback query"""
    with patch('handlers.balance_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_api, \
         patch('handlers.balance_handlers.get_earn_balances', return_value=mock_earn_data):
        mock_get_api.return_value = mock_selected_api
        
        await sendEarn(update, context)
        
        # Check final message
        final_call = update.callback_query.edit_message_text.call_args
        message_text = final_call[1]['text']
        reply_markup = final_call[1]['reply_markup']
        
        # Check content
        assert "🔑 Using API: Test API" in message_text
        assert "BTC" in message_text
        assert "Amount: 0.10000000" in message_text
        assert "APR: 5.00%" in message_text
        assert "Value: 3,000.00 USDT" in message_text
        assert isinstance(reply_markup, InlineKeyboardMarkup)
        assert reply_markup.inline_keyboard[0][0].callback_data == "refresh_earn"

@pytest.mark.asyncio
async def test_send_earn_no_positions(update, context, mock_selected_api):
    """Test sendEarn with no earn positions"""
    update.callback_query = None
    empty_earn_data = {
        'account1': {
            'name': 'Test Account',
            'holdings': []
        }
    }
    
    with patch('handlers.balance_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_api, \
         patch('handlers.balance_handlers.get_earn_balances', return_value=empty_earn_data):
        mock_get_api.return_value = mock_selected_api
        
        await sendEarn(update, context)
        
        # Check final message
        calls = update.message.reply_text.call_args_list
        final_call = calls[-1]
        message_text = final_call[1]['text']
        
        assert "No active earn positions found" in message_text

@pytest.mark.asyncio
async def test_send_earn_with_error(update, context, mock_selected_api):
    """Test error handling in sendEarn"""
    update.callback_query = None
    
    with patch('handlers.balance_handlers.get_selected_api', new_callable=AsyncMock) as mock_get_api, \
         patch('handlers.balance_handlers.get_earn_balances', side_effect=Exception("Test error")):
        mock_get_api.return_value = mock_selected_api
        
        await sendEarn(update, context)
        
        # Verify error message
        calls = update.message.reply_text.call_args_list
        final_call = calls[-1]
        assert final_call[0][0] == "Error getting earn positions: Test error"

@pytest.mark.asyncio
async def test_refresh_earn(update, context):
    """Test refresh_earn handler"""
    with patch('handlers.balance_handlers.sendEarn') as mock_send_earn:
        await refresh_earn(update, context)
        
        update.callback_query.answer.assert_called_once()
        mock_send_earn.assert_called_once_with(update, context)
