import streamlit as st
import threading
from telegram_bot import main as run_bot
import time

def run_telegram_bot():
    run_bot()

def main():
    st.set_page_config(page_title="Crypto Checker Bot")
    
    st.title("Crypto Checker Bot is running")
    
    # Add a status indicator
    status = st.empty()
    status.success("Bot is active and monitoring...")
    
    # Run the Telegram bot in a separate thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    # Keep the streamlit app running
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
