import gate_api
import streamlit as st

def get_all_clients():
    clients = {}
    for key in st.secrets["gate_io"]:
        if key.startswith("account"):
            configuration = gate_api.Configuration(
                key=st.secrets["gate_io"][key]["api_key"],
                secret=st.secrets["gate_io"][key]["api_secret"]
            )
            clients[key] = {
                "client": gate_api.ApiClient(configuration),
                "name": st.secrets["gate_io"][key]["name"]
            }
    return clients

def get_balance(account_name=None):
    clients = get_all_clients()
    
    if account_name and account_name in clients:
        wallet_api = gate_api.WalletApi(clients[account_name]["client"])
        return {
            "name": clients[account_name]["name"],
            "balance": float(wallet_api.get_total_balance().total.amount)
        }
    
    # Get all balances if no specific account is specified
    balances = {}
    total = 0
    for acc_name, client_data in clients.items():
        wallet_api = gate_api.WalletApi(client_data["client"])
        balance = float(wallet_api.get_total_balance().total.amount)
        balances[acc_name] = {
            "name": client_data["name"],
            "balance": balance
        }
        total += balance
    
    balances["total"] = total
    return balances

def get_usdt_price(spot_api, currency):
    if currency == 'USDT':
        return 1.0
    try:
        ticker = spot_api.list_tickers(currency_pair=f"{currency}_USDT")
        return float(ticker[0].last)
    except:
        return 0.0

def get_spot_holdings(account_name=None, min_usdt_value=0.5):
    clients = get_all_clients()
    
    if account_name and account_name in clients:
        spot_api = gate_api.SpotApi(clients[account_name]["client"])
        balances = spot_api.list_spot_accounts()
        holdings = []
        
        for b in balances:
            available = float(b.available)
            locked = float(b.locked)
            total = available + locked
            if total > 0:
                price = get_usdt_price(spot_api, b.currency)
                usdt_value = total * price
                if usdt_value >= min_usdt_value:
                    holdings.append({
                        "currency": b.currency,
                        "available": available,
                        "locked": locked,
                        "total": total,
                        "price_usdt": price,
                        "value_usdt": usdt_value
                    })
        
        return {
            "name": clients[account_name]["name"],
            "holdings": sorted(holdings, key=lambda x: x['value_usdt'], reverse=True)
        }
    
    # Get all accounts holdings
    all_holdings = {}
    for acc_name, client_data in clients.items():
        spot_api = gate_api.SpotApi(client_data["client"])
        balances = spot_api.list_spot_accounts()
        holdings = []
        
        for b in balances:
            available = float(b.available)
            locked = float(b.locked)
            total = available + locked
            if total > 0:
                price = get_usdt_price(spot_api, b.currency)
                usdt_value = total * price
                if usdt_value >= min_usdt_value:
                    holdings.append({
                        "currency": b.currency,
                        "available": available,
                        "locked": locked,
                        "total": total,
                        "price_usdt": price,
                        "value_usdt": usdt_value
                    })
        
        all_holdings[acc_name] = {
            "name": client_data["name"],
            "holdings": sorted(holdings, key=lambda x: x['value_usdt'], reverse=True)
        }
    
    return all_holdings

if __name__ == '__main__':
    balances = get_balance()
    print(balances)