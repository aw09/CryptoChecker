import streamlit as st
import asyncio
from telegram_bot import main as run_bot, stop as stop_bot
import logging
import nest_asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

def run_bot_in_thread():
    try:
        asyncio.run(run_bot())
    except Exception as e:
        logger.error(f"Bot thread error: {e}")

def main():
    st.set_page_config(page_title="Crypto Checker Bot")
    st.title("Crypto Checker Bot is running")
    
    # Initialize session state
    if 'bot_status' not in st.session_state:
        st.session_state.bot_status = 'stopped'
        st.session_state.bot_thread = None
    
    # Add status indicators
    status = st.empty()
    
    # Add start/stop button
    if st.button('Start/Stop Bot'):
        if st.session_state.bot_status == 'running':
            try:
                asyncio.run(stop_bot())
                st.session_state.bot_status = 'stopped'
                status.warning("Bot stopped")
            except Exception as e:
                status.error(f"Error stopping bot: {str(e)}")
        else:
            st.session_state.bot_status = 'running'
            
    # Handle bot status
    if st.session_state.bot_status == 'running':
        status.success("Bot is active and monitoring...")
        if st.session_state.bot_thread is None:
            import threading
            thread = threading.Thread(target=run_bot_in_thread, daemon=True)
            thread.start()
            st.session_state.bot_thread = thread
    else:
        status.info("Bot is stopped. Click the button to start.")

if __name__ == "__main__":
    main()
