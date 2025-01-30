import streamlit as st
import asyncio
from telegram_bot import main as run_bot
import logging
import threading
import nest_asyncio

# Configure logging with proper format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Override any existing configuration
)
logger = logging.getLogger(__name__)

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

def run_bot_forever():
    try:
        asyncio.run(run_bot())
    except Exception as e:
        logger.error(f"Bot error: {e}")

def main():
    st.set_page_config(page_title="Crypto Checker Bot")
    st.title("Crypto Checker Bot")
    
    # Start bot in background thread if not already running
    if 'bot_thread' not in st.session_state:
        thread = threading.Thread(target=run_bot_forever, daemon=True)
        thread.start()
        st.session_state.bot_thread = thread
    
    # Simple interface
    st.info("Bot is running and monitoring Telegram commands")

if __name__ == "__main__":
    main()
