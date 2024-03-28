from dotenv import load_dotenv
import os

load_dotenv()

# Binance
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET = os.getenv("BINANCE_SECRET")

# Gate
GATE_API_KEY = os.getenv("GATE_API_KEY")
GATE_SECRET = os.getenv("GATE_SECRET")

# Wallet
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")