import gate_api
from configs import GATE_API_KEY, GATE_SECRET

# Configure the API host
configuration = gate_api.Configuration(
    # host="https://api.gate.io/api/v4",
    key=GATE_API_KEY,
    secret=GATE_SECRET,
)

# Create an API client
api_client = gate_api.ApiClient(configuration)

def get_balance():
    wallet_api = gate_api.WalletApi(api_client)
    balance = float(wallet_api.get_total_balance().total.amount)
    return balance


if __name__ == '__main__':
    balance = get_balance()
    print(balance)