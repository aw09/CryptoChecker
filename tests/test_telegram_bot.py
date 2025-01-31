import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message
from telegram.ext import ContextTypes, ApplicationBuilder
from telegram_bot import (
    get_application, authorization, read_whitelist,
    setup_commands, setup_handlers, run_bot
)

# Fixtures
@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.username = "test_user"
    update.effective_user.id = "12345"
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    return update

@pytest.fixture
def mock_context():
    return MagicMock(spec=ContextTypes.DEFAULT_TYPE)

# Test application initialization
@pytest.mark.asyncio
async def test_get_application():
    with patch('telegram_bot.ApplicationBuilder') as mock_builder:
        mock_app = MagicMock()
        mock_builder.return_value.token.return_value.build.return_value = mock_app
        
        app1 = get_application()
        app2 = get_application()
        
        assert app1 == app2  # Should return same instance
        assert mock_builder.call_count == 1  # Should only create once

# Test authorization decorator
@pytest.mark.asyncio
async def test_authorization_allowed(mock_update, mock_context):
    with patch('telegram_bot.read_whitelist', return_value=['test_user', '12345']):
        @authorization
        async def test_func(update, context):
            return True
        
        result = await test_func(mock_update, mock_context)
        assert result is True
        assert not mock_update.message.reply_text.called

@pytest.mark.asyncio
async def test_authorization_denied(mock_update, mock_context):
    with patch('telegram_bot.read_whitelist', return_value=['other_user']):
        @authorization
        async def test_func(update, context):
            return True
        
        await test_func(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once_with('You are not authorized to use this bot.')

# Test whitelist reading
def test_read_whitelist():
    with patch('streamlit.secrets', {'whitelist': {'usernames': ['user1', 'user2']}}):
        whitelist = read_whitelist()
        assert isinstance(whitelist, list)
        assert 'user1' in whitelist
        assert 'user2' in whitelist

# Test command setup
@pytest.mark.asyncio
async def test_setup_commands():
    mock_app = MagicMock()
    mock_app.bot.set_my_commands = AsyncMock()
    
    await setup_commands(mock_app)
    mock_app.bot.set_my_commands.assert_called_once()

# Test bot running
@pytest.mark.asyncio
async def test_run_bot():
    with patch('telegram_bot.get_application') as mock_get_app:
        mock_app = MagicMock()
        mock_app.run_polling = AsyncMock()
        mock_get_app.return_value = mock_app
        
        await run_bot()
        mock_app.run_polling.assert_called_once()

# Test handler setup
def test_setup_handlers():
    mock_app = MagicMock()
    mock_app.add_handler = MagicMock()
    
    setup_handlers(mock_app)
    
    # Verify that handlers were added
    assert mock_app.add_handler.call_count > 0

# Test conversation handlers
@pytest.mark.asyncio
async def test_api_conversation_flow(mock_update, mock_context):
    from telegram_bot import add_api_start, APIKEY
    
    result = await add_api_start(mock_update, mock_context)
    assert result == APIKEY
    mock_update.message.reply_text.assert_called_once()

@pytest.mark.asyncio
async def test_alert_conversation_flow(mock_update, mock_context):
    from telegram_bot import add_alert_start, ALERT_COIN
    
    result = await add_alert_start(mock_update, mock_context)
    assert result == ALERT_COIN
    mock_update.message.reply_text.assert_called_once()