import pytest
from unittest.mock import Mock, patch
import gate_api
from gate_script import (
    get_client, check_ticker_exists, get_balance, get_usdt_price,
    get_spot_holdings, check_current_price, get_multiple_prices,
    get_earn_balances, redeem_from_earn, get_lending_rates
)

# Test constants
TEST_API_KEY = "test_key"
TEST_API_SECRET = "test_secret"

@pytest.fixture
def mock_gate_api():
    with patch('gate_api.ApiClient') as mock_client:
        with patch('gate_api.SpotApi') as mock_spot:
            with patch('gate_api.WalletApi') as mock_wallet:
                with patch('gate_api.EarnUniApi') as mock_earn_uni:  # Changed from EarnApi to EarnUniApi
                    yield {
                        'client': mock_client,
                        'spot': mock_spot,
                        'wallet': mock_wallet,
                        'earn_uni': mock_earn_uni  # Changed key name
                    }

def test_get_client():
    client = get_client(TEST_API_KEY, TEST_API_SECRET)
    assert client['name'] == "Selected Account"
    assert isinstance(client['client'], gate_api.ApiClient)

def test_check_ticker_exists(mock_gate_api):
    mock_ticker = Mock()
    mock_ticker.last = "1.0"
    mock_gate_api['spot'].return_value.list_tickers.return_value = [mock_ticker]
    
    result = check_ticker_exists(TEST_API_KEY, TEST_API_SECRET, "BTC")
    assert result is True

def test_get_balance(mock_gate_api):
    mock_balance = Mock()
    mock_balance.total.amount = "1000.0"
    mock_gate_api['wallet'].return_value.get_total_balance.return_value = mock_balance
    
    result = get_balance(TEST_API_KEY, TEST_API_SECRET)
    assert result['total'] == 1000.0
    assert result['account1']['balance'] == 1000.0

def test_get_spot_holdings(mock_gate_api):
    mock_account = Mock()
    mock_account.currency = "BTC"
    mock_account.available = "1.0"
    mock_account.locked = "0.5"
    mock_gate_api['spot'].return_value.list_spot_accounts.return_value = [mock_account]
    
    # Mock ticker response
    mock_ticker = Mock()
    mock_ticker.last = "30000.0"
    mock_gate_api['spot'].return_value.list_tickers.return_value = [mock_ticker]
    
    result = get_spot_holdings(TEST_API_KEY, TEST_API_SECRET)
    holdings = result['account1']['holdings']
    assert len(holdings) == 1
    assert holdings[0]['currency'] == "BTC"
    assert holdings[0]['total'] == 1.5
    assert holdings[0]['value_usdt'] == 45000.0

def test_check_current_price(mock_gate_api):
    mock_ticker = Mock()
    mock_ticker.last = "30000.0"
    mock_gate_api['spot'].return_value.list_tickers.return_value = [mock_ticker]
    
    price = check_current_price(TEST_API_KEY, TEST_API_SECRET, "BTC")
    assert price == 30000.0

def test_get_multiple_prices(mock_gate_api):
    mock_ticker1 = Mock()
    mock_ticker1.currency_pair = "BTC_USDT"
    mock_ticker1.last = "30000.0"
    
    mock_ticker2 = Mock()
    mock_ticker2.currency_pair = "ETH_USDT"
    mock_ticker2.last = "2000.0"
    
    mock_gate_api['spot'].return_value.list_tickers.return_value = [mock_ticker1, mock_ticker2]
    
    prices = get_multiple_prices(TEST_API_KEY, TEST_API_SECRET, ["BTC", "ETH"])
    assert prices["BTC"] == 30000.0
    assert prices["ETH"] == 2000.0

def test_get_earn_balances(mock_gate_api):
    mock_record = Mock()
    mock_record.currency = "HYPE"
    mock_record.amount = "60.096923"
    mock_record.frozen_amount = "0"
    mock_record.interest_status = "interest_reinvest"
    mock_record.min_rate = "0.000005"
    mock_record.create_time = 1738080416173
    mock_record.update_time = 1738258595517
    
    # Mock the ticker response for price calculation
    mock_ticker = Mock()
    mock_ticker.last = "1.5"  # Example USDT price
    mock_gate_api['spot'].return_value.list_tickers.return_value = [mock_ticker]
    
    mock_gate_api['earn_uni'].return_value.list_user_uni_lends.return_value = [mock_record]
    
    result = get_earn_balances(TEST_API_KEY, TEST_API_SECRET)
    holdings = result['account1']['holdings']
    assert len(holdings) == 1
    assert holdings[0]['currency'] == "HYPE"
    assert holdings[0]['amount'] == 60.096923
    assert holdings[0]['frozen_amount'] == 0
    assert holdings[0]['interest_status'] == "interest_reinvest"
    assert holdings[0]['value_usdt'] == 60.096923 * 1.5  # amount * price

def test_redeem_from_earn(mock_gate_api):
    # Mock redemption response (None for success)
    mock_gate_api['earn_uni'].return_value.create_uni_lend.return_value = None
    
    result = redeem_from_earn(TEST_API_KEY, TEST_API_SECRET, "USDT", 100.0)
    assert result['status'] == "success"
    assert result['currency'] == "USDT"
    assert result['amount'] == 100.0

def test_redeem_all_from_earn(mock_gate_api):
    # Mock earn balance
    mock_record = Mock()
    mock_record.currency = "BTC"
    mock_record.amount = "0.5"
    mock_gate_api['earn_uni'].return_value.list_user_uni_lends.return_value = [mock_record]
    
    # Mock redemption response (None for success)
    mock_gate_api['earn_uni'].return_value.create_uni_lend.return_value = None
    
    result = redeem_from_earn(TEST_API_KEY, TEST_API_SECRET, "BTC", redeem_all=True)
    assert result['status'] == "success"
    assert result['currency'] == "BTC"
    assert result['amount'] == 0.5

def test_get_lending_rates(mock_gate_api):
    mock_currency = Mock()
    mock_currency.currency = "BTC"
    mock_currency.min_rate = "0.00000102"
    mock_currency.max_rate = "0.00057"
    mock_currency.min_lend_amount = "0.00001"
    mock_currency.max_lend_amount = "120000000"
    
    # Update to use earn_uni instead of earn
    mock_gate_api['earn_uni'].return_value.list_uni_currencies.return_value = [mock_currency]
    
    rates = get_lending_rates(TEST_API_KEY, TEST_API_SECRET)
    assert "BTC" in rates
    assert rates["BTC"]["min_rate"] == 0.00000102
    assert rates["BTC"]["max_rate"] == 0.00057
    assert rates["BTC"]["min_amount"] == 0.00001
    assert rates["BTC"]["max_amount"] == 120000000

def test_error_handling():
    with pytest.raises(ValueError):
        get_balance()
    
    with pytest.raises(ValueError):
        get_spot_holdings()
    
    with pytest.raises(ValueError):
        get_earn_balances()
