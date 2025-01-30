import streamlit as st
import asyncio
from telegram_bot import get_application, run_bot
from handlers.alert_handlers import check_alerts
import logging
import threading
import nest_asyncio
import time
import socket
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

async def run_bot_and_workers():
    """Run both the bot and alert checker worker"""
    app = get_application()
    
    try:
        # Run both the bot and alert checker concurrently
        await asyncio.gather(
            run_bot(),
            check_alerts(app.bot)
        )
    except Exception as e:
        logger.error(f"Error in bot or worker: {e}", exc_info=True)
        raise

def run_bot_forever():
    # Remove extra loop creation and closing
    while True:
        try:
            asyncio.run(run_bot_and_workers())
        except Exception as e:
            logger.error(f"Bot error: {e}", exc_info=True)
            time.sleep(5)

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org')
        return response.text
    except:
        return "Unable to get public IP"

def main():
    st.set_page_config(page_title="Crypto Checker Bot")
    st.title("Crypto Checker Bot")
    
    public_ip = get_public_ip()
    logger.info(f"Running on Public IP: {public_ip}")
    print(f"Running on Public IP: {public_ip}")
    
    # Start bot in background thread if not already running
    if 'bot_thread' not in st.session_state:
        thread = threading.Thread(target=run_bot_forever, daemon=True)
        thread.start()
        st.session_state.bot_thread = thread
    
    # Simple interface
    st.info("Bot is running and monitoring Telegram commands")

if __name__ == "__main__":
    main()
