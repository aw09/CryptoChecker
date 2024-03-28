from binance_script import get_balance as binance_balance
from gate_script import balance as gate_balance
from wallet_script import balance_usdt as wallet_balance
import os

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