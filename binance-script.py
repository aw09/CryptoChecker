import pandas as pd
from binance.spot import Spot as Client
import time
from datetime import datetime, timedelta
from utils import format_currency, get_datetime_now
from configs import BINANCE_API_KEY, BINANCE_SECRET
import time
from binance.websocket.spot.websocket_api import SpotWebsocketAPIClient
from websocket import WebSocketTimeoutException
import os
import json
import threading
import logging

pd.options.display.float_format = '{:.5f}'.format
pd.set_option('display.max_columns', None)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.precision', 2)

client = Client(BINANCE_API_KEY, BINANCE_SECRET)
last_updated = get_datetime_now()
websocket_client = None

# Get USDT/IDR exchange rate
usdt_idr_ticker = client.ticker_price("USDTIDRT")
usdt_idr_rate = float(usdt_idr_ticker['price'])

# Get the current date and time
now = datetime.now()

# Subtract one year
one_year_ago = now - timedelta(days=200)

# Convert to timestamp and then to milliseconds
start_time = int(time.mktime(one_year_ago.timetuple()) * 1000)
end_time = int(time.mktime(now.timetuple()) * 1000)
tes = client.convert_history(startTime=start_time, endTime=end_time)

# Get account information
account_info = client.account()
earns = client.get_flexible_product_position()

asset_earn = []
total_asset_earns = 0
total_rewards_earns = 0
for earn in earns['rows']:
    total_asset_earns += float(earn['totalAmount'])
    total_rewards_earns += float(earn['cumulativeTotalRewards'])
    asset_earn.append([earn['asset'], earn['totalAmount'], earn['cumulativeTotalRewards'], earn['yesterdayRealTimeRewards']])

df_earn = pd.DataFrame(asset_earn, columns=['Asset', 'Total Amount', 'Cumulative Total Rewards', 'Yesterday Real Time Rewards'])
print(f"\r=== Earns ===")
print(df_earn)
print(f"Total Asset Earns: {total_asset_earns}")
print(f"Total Asset Earns in IDR: {format_currency(total_asset_earns * usdt_idr_rate)}")


current_prices = {}

def calculate_asset():
    global last_updated
    last_updated = datetime.now()

    asset_data = []
    total_value = 0
    total_profit_loss = 0
    for asset in account_info['balances']:
        if float(asset['free']) > 0:
            symbol = asset['asset'] + "USDT"
            try:
                # Get the current price
                current_price = current_prices.get(symbol, 0)
                if current_price == 0:
                    ticker = client.ticker_price(symbol)
                    current_price = float(ticker['price'])
                
                if float(asset['free']) * current_price > 1:
                    # Fetch all trades for the symbol
                    trades = client.my_trades(symbol)

                    # Calculate the total cost and total quantity
                    total_cost = 0
                    total_qty = 0
                    for trade in trades:
                        if trade['isBuyer']:
                            total_cost += float(trade['price']) * float(trade['qty'])
                            total_qty += float(trade['qty'])
                        else:
                            total_cost -= float(trade['price']) * float(trade['qty'])
                            total_qty -= float(trade['qty'])
                            if total_qty < 0:
                                total_qty = 0
                                total_cost = 0
                    
                    # Calculate the average cost
                    avg_price = total_cost / total_qty if total_qty > 0 else 0

                    # Current asset value
                    asset_value = float(asset['free']) * current_price
                    
                    # Calculate the percentage change
                    pct_change = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0


                    # Calculate the profit or loss
                    profit_loss = asset_value - total_cost
                    total_profit_loss += profit_loss
                    
                    asset_value = float(asset['free']) * current_price
                    total_value += asset_value
                    asset_data.append([asset['asset'], asset['free'], avg_price, total_cost, current_price, asset_value, profit_loss, pct_change])
            except Exception as e:
                continue

    # Create a DataFrame and print it
    df = pd.DataFrame(asset_data, columns=['Asset', 'Free', 'Average Price', 'Total Cost', 'Current Price', 'Current Value', 'Profit/Loss', 'Percentage Change'])
    df = df.sort_values('Current Value', ascending=False)
    os.system('clear')

    # Print the DataFrame
    print(f"Updated at: {last_updated}")
    print(f"=== Assets ===")
    print(df)

    # Convert total value to IDR
    total_value_idr = total_value * usdt_idr_rate

    # Print total value of assets
    print(f"Total value of assets in USDT: {total_value}")
    print(f"USDT/IDR exchange rate: {usdt_idr_rate}")
    print(f"Total value of assets in IDR: {format_currency(total_value_idr)}")
    print(f"Total profit/loss in USDT: {total_profit_loss}")
    print(f"Total profit/loss in IDR: {format_currency(total_profit_loss * usdt_idr_rate)}")

    print(f"Total All Earns and Asset: {total_asset_earns + total_value}")
    print(f"Total All Earns and Asset in IDR: {format_currency((total_asset_earns + total_value) * usdt_idr_rate)}")

def message_handler(_, message):
    message = json.loads(message)
    if message['status'] == 200:
        result = message['result']
        symbol = result['symbol']
        price = float(result['lastPrice'])
        current_prices[symbol] = price
        calculate_asset()

def error_handler(_, message):
    print(f"Error: {message}")


def heartbeat(ws: SpotWebsocketAPIClient):
    global last_updated
    while True:
        try:
            logging.warning("== Heartbeat ==")
            logging.warning(ws)
            time.sleep(30)  # check every 30 seconds
            if (datetime.now() - last_updated).total_seconds() > 30:  # if last update was more than 30 seconds ago
                print("No updates in the last 30 seconds, reconnecting...")
                connect_to_websocket()
                break
        except Exception:
            print("WebSocket connection timed out. Reconnecting...")
            time.sleep(5)
            connect_to_websocket()
            break


def pong_handler(ws):
    print("Received pong ==")


def connect_to_websocket():
    global websocket_client
    while True:
        try:
            if websocket_client is None:
                websocket_client = SpotWebsocketAPIClient(
                    api_key=BINANCE_API_KEY,
                    api_secret=BINANCE_SECRET,
                    on_message=message_handler,
                    on_error=error_handler,
                    on_pong=pong_handler,
                    timeout=60
                )
            for asset in account_info['balances']:
                if float(asset['free']) > 0:
                    symbol = asset['asset'] + "USDT"
                    websocket_client.ticker(symbol=symbol, type="FULL")

            # Start the heartbeat thread
            threading.Thread(target=heartbeat, args=(websocket_client,)).start()
            break
        except Exception:
            print("WebSocket connection timed out. Reconnecting...")
            time.sleep(5)
            websocket_client = None

connect_to_websocket()