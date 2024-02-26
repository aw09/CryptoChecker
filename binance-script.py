import pandas as pd
from binance.spot import Spot as Client
import time
from datetime import datetime, timedelta
from utils import format_currency
from configs import BINANCE_API_KEY, BINANCE_SECRET

pd.options.display.float_format = '{:.5f}'.format
pd.set_option('display.max_columns', None)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.precision', 2)

client = Client(BINANCE_API_KEY, BINANCE_SECRET)

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
print(f"=== Earns ===")
print(df_earn)
print(f"Total Asset Earns: {total_asset_earns}")
print(f"Total Asset Earns in IDR: {format_currency(total_asset_earns * usdt_idr_rate)}")

asset_data = []
total_value = 0
total_profit_loss = 0
for asset in account_info['balances']:
    if float(asset['free']) > 0:
        symbol = asset['asset'] + "USDT"  # Assuming you want the price in USDT
        try:
            # Get the current price
            ticker = client.ticker_price(symbol)
            current_price = float(ticker['price'])

            # Fetch all trades for the symbol
            trades = client.my_trades(symbol)

            if symbol == "MATICUSDT":
                pass


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
            # print(f"Could not fetch trades for {symbol}. Error: {e}")
            continue  # Skip the current asset and move to the next one

# Create a DataFrame and print it
df = pd.DataFrame(asset_data, columns=['Asset', 'Free', 'Average Price', 'Total Cost', 'Current Price', 'Current Value', 'Profit/Loss', 'Percentage Change'])
df = df.sort_values('Current Value', ascending=False)

# Print the DataFrame
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