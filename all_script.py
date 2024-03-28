from binance_script import get_balance as binance_balance
from gate_script import balance as gate_balance


total_binance, usdt_idr_rate = binance_balance()
total_gate = gate_balance

print("=== BINANCE ===")
print(f"Total Asset in USDT: {format(total_binance, ',.0f')}")
print(f"Total Asset in IDR: {format(total_binance * usdt_idr_rate, ',.0f')}")

print("=== GATE.IO ===")
print(f"Total Asset in USDT: {total_gate}")
print(f"Total Asset in IDR: {format(total_gate * usdt_idr_rate, ',.0f')}")

print("=== TOTAL ===")
print(f"Total Asset in USDT: {format(total_binance + total_gate, ',.0f')}")
print(f"Total Asset in IDR: {format((total_binance + total_gate) * usdt_idr_rate, ',.0f')}")