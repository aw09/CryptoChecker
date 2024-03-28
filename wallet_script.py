from binance.spot import Spot as Client
from configs import BINANCE_API_KEY, BINANCE_SECRET, WALLET_ADDRESS
from web3 import Web3

# Connect to an Optimism node
w3 = Web3(Web3.HTTPProvider('https://mainnet.optimism.io'))

client = Client(BINANCE_API_KEY, BINANCE_SECRET)
eth_price = client.ticker_price("ETHUSDT")


# Get the balance
balance = w3.eth.get_balance(WALLET_ADDRESS) / 10**18
balance_usdt = balance * float(eth_price['price'])


if __name__ == '__main__':
    print(f"ETH Balance: {balance}")
    print(f"Total Asset in USDT: {balance_usdt}")


