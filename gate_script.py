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

if __name__ == '__main__':
    balances = get_balance()
    print(balances)