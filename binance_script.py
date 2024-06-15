import pandas as pd
from binance.spot import Spot as Client
from datetime import datetime
from utils import format_currency, get_datetime_now
from configs import BINANCE_API_KEY, BINANCE_SECRET
import time
import os
import json
import sys
import time
import argparse

pd.options.display.float_format = '{:.5f}'.format
pd.set_option('display.max_columns', None)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.precision', 2)

client = Client(BINANCE_API_KEY, BINANCE_SECRET)

# Get USDT/IDR exchange rate
usdt_idr_ticker = client.ticker_price("USDTIDRT")
USDT_IDR_RATE = float(usdt_idr_ticker['price'])

# GLOBAL VARIABLE
LAST_UPDATED = get_datetime_now()
BALANCE_DICT = {}
SPOT_ASSET = ['BTCUSDT']
PRICE_DICT = {}
ACCOUNT_INFO = None
BALANCE = None
TOTAL_ASSET_IN_BTC, TOTAL_ASSET_IN_USDT, TOTAL_PROFIT_LOSS, TOTAL_SPOT_VALUE = 0, 0, 0, 0


def get_balance():
    global BALANCE_DICT, BALANCE, TOTAL_ASSET_IN_USDT, TOTAL_SPOT_VALUE, TOTAL_ASSET_IN_BTC
    usdt_idr_ticker = client.ticker_price("USDTIDRT")
    USDT_IDR_RATE = float(usdt_idr_ticker['price'])
    BALANCE = client.balance()
    BALANCE_DICT = {item['walletName']: float(item['balance']) for item in BALANCE}

    prices = client.ticker_price(symbols=SPOT_ASSET)
    PRICE_DICT = {item['symbol']: float(item['price']) for item in prices}
    
    TOTAL_SPOT_VALUE = BALANCE_DICT.get('Spot', 0) * PRICE_DICT.get('BTCUSDT', 0)
    TOTAL_ASSET_IN_BTC = sum([float(x['balance']) for x in BALANCE if float(x['balance']) > 0])
    TOTAL_ASSET_IN_USDT = TOTAL_ASSET_IN_BTC * float(PRICE_DICT.get('BTCUSDT', 0))
    
    return TOTAL_ASSET_IN_USDT, USDT_IDR_RATE


def get_spot_asset():
    global SPOT_ASSET, ACCOUNT_INFO
    ACCOUNT_INFO = client.account()
    exclusion1 = ['USDT','ETHFI', 'FDUSDT']
    exclusion1 += ['LD' + x for x in exclusion1]
    exclusion2 = ['LD' + x['asset'] for x in ACCOUNT_INFO['balances']]
    exclusions = exclusion1 + exclusion2
    SPOT_ASSET += [x['asset'] + "USDT" for x in ACCOUNT_INFO['balances'] if float(x['free']) > 0 and x['asset'] not in exclusions]
    



def calculate_asset(sort_by='Current Value'):
    global LAST_UPDATED, SPOT_ASSET, PRICE_DICT, ACCOUNT_INFO, BALANCE, TOTAL_PROFIT_LOSS
    LAST_UPDATED = datetime.now()

    prices = client.ticker_price(symbols=SPOT_ASSET)
    PRICE_DICT = {item['symbol']: float(item['price']) for item in prices}

    asset_data = []
    for asset in ACCOUNT_INFO['balances']:
        if float(asset['free']) > 0 :
            symbol = asset['asset'] + "USDT"
            try:
                # Get the current price
                current_price = PRICE_DICT.get(symbol, 0)
                
                if float(asset['free']) * current_price > 1:
                    # Fetch all trades for the symbol
                    trades = client.my_trades(symbol)
                    try:
                        fdusd_trades = (client.my_trades(symbol.replace('USDT', 'FDUSD')))
                        trades += fdusd_trades
                    except:
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
                    TOTAL_PROFIT_LOSS += profit_loss
                    
                    asset_value = float(asset['free']) * current_price
                    asset_data.append([asset['asset'], asset['free'], avg_price, total_cost, current_price, asset_value, profit_loss, pct_change])
            except Exception as e:
                continue

    # Create a DataFrame and print it
    df = pd.DataFrame(asset_data, columns=['Asset', 'Free', 'Average Price', 'Total Cost', 'Current Price', 'Current Value', 'Profit/Loss', 'Percentage Change'])
    df = df.sort_values(sort_by, ascending=False)

    return df


def print_df(df):
    global LAST_UPDATED, USDT_IDR_RATE, TOTAL_ASSET_IN_USDT, TOTAL_PROFIT_LOSS, TOTAL_SPOT_VALUE
    os.system('clear')

    print(df)
    print(f"\n\nUpdated at: {LAST_UPDATED}")
    print(f"USDT/IDR exchange rate: {USDT_IDR_RATE}")


    print(f"\n\n=== SPOT ===")
    print(f"Total Spot in USDT: {TOTAL_SPOT_VALUE}")
    print(f"Total Spot in IDR: {format_currency(TOTAL_SPOT_VALUE * USDT_IDR_RATE)}")
    print(f"Total profit/loss in USDT: {TOTAL_PROFIT_LOSS}")
    print(f"Total profit/loss in IDR: {format_currency(TOTAL_PROFIT_LOSS * USDT_IDR_RATE)}")
    print("==================================== \n\n")


    print(f"Total All Asset in USDT: {TOTAL_ASSET_IN_USDT}")
    print(f"Total All Asset in IDR: {format_currency(TOTAL_ASSET_IN_USDT * USDT_IDR_RATE)}")

def main(print_output=True):
    parser = argparse.ArgumentParser()
    parser.add_argument('--sortby', default='Current Value')
    parser.add_argument('--loops', type=int, default=1)
    parser.add_argument('--interval', type=int, default=1)
    args = parser.parse_args()

    sort_by = args.sortby
    loops = args.loops
    interval = args.interval

    loop_count = 0
    while loops == -1 or loop_count < loops:
        get_balance()
        get_spot_asset()
        df = calculate_asset(sort_by=sort_by)
        if print_output:
            print_df(df)
        loop_count += 1
        time.sleep(interval)

if __name__ == "__main__":
    # python3 binance-script.py --sortby="Percentage Change" --loops=5 --interval=5
    main()