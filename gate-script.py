import gate_api
from gate_api.exceptions import ApiException, GateApiException
from configs import GATE_API_KEY, GATE_SECRET
import pandas as pd
import time
from datetime import datetime, timedelta
from time import sleep
from utils import subtract_days_from_timestamp, get_now

# Configure the API host
configuration = gate_api.Configuration(
    # host="https://api.gate.io/api/v4",
    key=GATE_API_KEY,
    secret=GATE_SECRET,
)

# Create an API client
api_client = gate_api.ApiClient(configuration)

# Create an instance of the API class
wallet_api = gate_api.WalletApi(api_client)

account_api = gate_api.AccountApi(api_client)
spot_api = gate_api.SpotApi(api_client)
trades = []
currencies = []
thread = None
try:
    # Get wallet data
    timestamp_now = spot_api.get_system_time().server_time
    # timestamp_now = get_now()
    _from = subtract_days_from_timestamp(timestamp_now, 60)
    to = subtract_days_from_timestamp(timestamp_now, 2)

    print(f'From: {_from}, To: {to}')
    # thread = spot_api.list_my_trades(async_req=True, _from=_from, to=to)
    thread = spot_api.list_my_trades_with_http_info(async_req=True)
    currencies = spot_api.list_tickers()
    api_response = spot_api.get_system_time()

except GateApiException as ex:
    print("Gate API exception, label: %s, message: %s\n" % (ex.label, ex.message))
except ApiException as e:
    print("Exception when calling WalletApi->list_wallets: %s\n" % e)


tes = 0
while thread._success == False:
    tes = thread.get()
    sleep(1)

balances = {}
costs = {}

# Iterate over trades
for trade in trades:
    # Get trade details
    currency_pair = trade._currency_pair
    base_currency, quote_currency = currency_pair.split('_')

    amount = float(trade.amount)
    price = float(trade.price)
    fee = float(trade.fee)
    side = trade.side

    # Adjust balances and costs
    if side == 'buy':
        # If you bought, you spent quote currency and received base currency
        balances[quote_currency] = balances.get(quote_currency, 0) - amount * price
        balances[base_currency] = balances.get(base_currency, 0) + amount - fee
        costs[base_currency] = costs.get(base_currency, 0) + amount * price
    else:
        # If you sold, you spent base currency and received quote currency
        balances[base_currency] = balances.get(base_currency, 0) - amount
        balances[quote_currency] = balances.get(quote_currency, 0) + amount * price - fee
        costs[quote_currency] = costs.get(quote_currency, 0) + amount * price


# Filter currencies
filtered_currencies = {currency.currency_pair.split('_')[0]: 
                       currency for currency in currencies 
                       if currency.currency_pair.endswith('_USDT') 
                       and currency.currency_pair.split('_')[0] in balances}


# Prepare data for DataFrame
data = []
for currency, balance in balances.items():
    if currency != 'USDT':
        cost = costs.get(currency, 0)
        average_value = cost / balance if balance != 0 else 0

        current_price = float(filtered_currencies[currency].last)

        # Calculate change from average value to current price
        change = (current_price - average_value) / average_value * 100 if average_value > 0 else 0

        data.append([currency, balance, average_value, current_price, change])

# Create DataFrame
df = pd.DataFrame(data, columns=['Currency', 'Balance', 'Average Value', 'Current Price', 'Change'])

# Print DataFrame
print(df)