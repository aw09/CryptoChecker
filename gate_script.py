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

# Create an instance of the API class
wallet_api = gate_api.WalletApi(api_client)

account_api = gate_api.AccountApi(api_client)
spot_api = gate_api.SpotApi(api_client)
balance = float(wallet_api.get_total_balance().total.amount)


if __name__ == '__main__':
    print(balance)