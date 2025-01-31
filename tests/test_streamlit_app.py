import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import streamlit as st
from streamlit_app import (
    run_bot_and_workers,
    run_bot_forever,
    get_public_ip,
    main
)

# Test get_public_ip function
def test_get_public_ip_success():
    mock_response = MagicMock()
    mock_response.text = "192.168.1.1"
    
    with patch('requests.get', return_value=mock_response):
        ip = get_public_ip()
        assert ip == "192.168.1.1"

def test_get_public_ip_failure():
    with patch('requests.get', side_effect=Exception("Connection error")):
        ip = get_public_ip()
        assert ip == "Unable to get public IP"

# Test run_bot_and_workers function
@pytest.mark.asyncio
async def test_run_bot_and_workers_success():
    mock_app = MagicMock()
    mock_bot = MagicMock()
    mock_app.bot = mock_bot
    
    with patch('streamlit_app.get_application', return_value=mock_app), \
         patch('streamlit_app.run_bot', new_callable=AsyncMock) as mock_run_bot, \
         patch('streamlit_app.check_alerts', new_callable=AsyncMock) as mock_check_alerts:
        
        # Create a task that will be cancelled after a short time
        task = asyncio.create_task(run_bot_and_workers())
        await asyncio.sleep(0.1)  # Give it some time to start
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_run_bot.assert_called_once()
        mock_check_alerts.assert_called_once_with(mock_bot)

@pytest.mark.asyncio
async def test_run_bot_and_workers_error():
    logger_mock = MagicMock()
    with patch('streamlit_app.logger', logger_mock), \
         patch('streamlit_app.get_application', side_effect=Exception("Test error")):
        
        # Run and catch the expected exception
        try:
            await run_bot_and_workers()
        except Exception:
            pass
        
        # Verify error was logged
        logger_mock.error.assert_called_once_with(
            "Error in bot or worker: Test error",
            exc_info=True
        )

# Test run_bot_forever function
def test_run_bot_forever():
    with patch('asyncio.run') as mock_run, \
         patch('time.sleep') as mock_sleep:
        
        # Simulate running for 3 iterations then raise exception to break the loop
        mock_run.side_effect = [
            None,  # First call succeeds
            Exception("Test error"),  # Second call fails
            KeyboardInterrupt  # Third call breaks the loop
        ]
        
        try:
            run_bot_forever()
        except KeyboardInterrupt:
            pass
        
        assert mock_run.call_count == 3
        assert mock_sleep.called

# Test main function
def test_main_first_run():
    mock_thread = MagicMock()
    
    with patch('streamlit.set_page_config') as mock_set_page_config, \
         patch('streamlit.title') as mock_title, \
         patch('streamlit.info') as mock_info, \
         patch('threading.Thread', return_value=mock_thread) as mock_thread_init, \
         patch('streamlit_app.get_public_ip', return_value="192.168.1.1"), \
         patch.dict(st.session_state, {}, clear=True):
        
        main()
        
        mock_set_page_config.assert_called_once()
        mock_title.assert_called_once()
        mock_info.assert_called_once()
        mock_thread_init.assert_called_once()
        mock_thread.start.assert_called_once()
        assert 'bot_thread' in st.session_state

def test_main_subsequent_run():
    mock_thread = MagicMock()
    
    with patch('streamlit.set_page_config') as mock_set_page_config, \
         patch('streamlit.title') as mock_title, \
         patch('streamlit.info') as mock_info, \
         patch('threading.Thread', return_value=mock_thread) as mock_thread_init, \
         patch('streamlit_app.get_public_ip', return_value="192.168.1.1"), \
         patch.dict(st.session_state, {'bot_thread': mock_thread}, clear=True):
        
        main()
        
        mock_set_page_config.assert_called_once()
        mock_title.assert_called_once()
        mock_info.assert_called_once()
        mock_thread_init.assert_not_called()
        mock_thread.start.assert_not_called()

# Test session state handling
def test_session_state_management():
    mock_thread = MagicMock()
    
    with patch.dict(st.session_state, {}, clear=True):
        assert 'bot_thread' not in st.session_state
        
        with patch('threading.Thread', return_value=mock_thread):
            main()
            assert 'bot_thread' in st.session_state
            assert st.session_state.bot_thread == mock_thread

# Test error handling
def test_main_with_errors():
    mock_logger = MagicMock()
    
    with patch('streamlit_app.get_public_ip', side_effect=Exception("Network error")), \
         patch('streamlit.error') as mock_error, \
         patch('streamlit_app.logger', mock_logger), \
         patch('logging.getLogger', return_value=mock_logger), \
         patch('builtins.print') as mock_print, \
         patch('streamlit.info'), \
         patch('streamlit.set_page_config'), \
         patch('streamlit.title'), \
         patch('threading.Thread'):
        
        try:
            main()
        except Exception:
            pass

        # Check that either the logger was used or print was called
        log_called = any([
            mock_logger.info.called,
            mock_logger.error.called,
            mock_print.called
        ])
        assert log_called, "Neither logger nor print was called"