from binance_script import get_balance as binance_balance, client
from gate_script import balance as gate_balance
from wallet_script import balance_usdt as wallet_balance
import os
import pandas as pd
from datetime import datetime

total_binance, usdt_idr_rate = binance_balance()
total_gate = gate_balance

os.system('clear')
print("=== BINANCE ===")
print(f"Total Asset in USDT: {format(total_binance, ',.0f')}")
print(f"Total Asset in IDR: {format(total_binance * usdt_idr_rate, ',.0f')}")

print("\n=== GATE.IO ===")
print(f"Total Asset in USDT: {total_gate}")
print(f"Total Asset in IDR: {format(total_gate * usdt_idr_rate, ',.0f')}")

print("\n=== WALLET ===")
print(f"Total Asset in USDT: {format(wallet_balance, ',.0f')}")
print(f"Total Asset in IDR: {format(wallet_balance * usdt_idr_rate, ',.0f')}")

print("\n=== TOTAL ===")
total_usdt = total_binance + total_gate + wallet_balance
total_idr = total_usdt * usdt_idr_rate
print(f"Total Asset in USDT: {format(total_usdt, ',.0f')}")
print(f"Total Asset in IDR: {format(total_idr, ',.0f')}")

print("\n=== Total + Bitget ===")
manta_bitget = 325
manta_price = client.ticker_price("MANTAUSDT")
total_bitget = manta_bitget * float(manta_price['price'])
total_usdt_with_bitget = total_usdt + total_bitget
total_idr_with_bitget = total_usdt_with_bitget * usdt_idr_rate
print(f"Total Asset in USDT: {format(total_usdt_with_bitget, ',.0f')}")
print(f"Total Asset in IDR: {format(total_idr_with_bitget, ',.0f')}")


# Check if the file exists
file_exists = os.path.isfile('balances.csv')

df = pd.DataFrame({
    'Date': [datetime.now()],
    'Binance_USDT': [total_binance],
    'Gate_USDT': [total_gate],
    'Wallet_USDT': [wallet_balance],
    'Total_USDT': [total_usdt],
    'Total_IDR': [total_idr],
    'Total_with_other_usdt': [total_usdt_with_bitget],
    'Total_with_other_idr': [total_idr_with_bitget]
})

# Append the DataFrame to the CSV file
df.to_csv('balances.csv', mode='a', header=not file_exists, index=False)