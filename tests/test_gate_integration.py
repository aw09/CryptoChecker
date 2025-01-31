import os
import pytest
from dotenv import load_dotenv
from gate_script import (
    get_balance, get_spot_holdings, check_current_price,
    get_multiple_prices, get_earn_balances, buy_spot, sell_spot
)

# Load environment variables from .env file
load_dotenv()

# Get API credentials from environment variables
API_KEY = os.getenv('GATE_API_KEY')
API_SECRET = os.getenv('GATE_API_SECRET')

# Add integration marker to all tests in this file
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not API_KEY or not API_SECRET,
        reason="API credentials not found in environment variables"
    )
]

def test_real_balance():
    """Test getting real balance"""
    result = get_balance(API_KEY, API_SECRET)
    assert 'total' in result
    assert isinstance(result['total'], float)
    assert 'account1' in result

def test_real_spot_holdings():
    """Test getting real spot holdings"""
    result = get_spot_holdings(API_KEY, API_SECRET)
    assert 'account1' in result
    assert 'holdings' in result['account1']
    for holding in result['account1']['holdings']:
        assert 'currency' in holding
        assert 'value_usdt' in holding
        assert isinstance(holding['value_usdt'], float)

def test_real_current_price():
    """Test getting real current price for BTC"""
    price = check_current_price(API_KEY, API_SECRET, "BTC")
    assert isinstance(price, float)
    assert price > 0

def test_real_multiple_prices():
    """Test getting real prices for multiple coins"""
    coins = ["BTC", "ETH", "USDT"]
    prices = get_multiple_prices(API_KEY, API_SECRET, coins)
    assert isinstance(prices, dict)
    assert "BTC" in prices
    assert "ETH" in prices
    assert all(isinstance(price, float) for price in prices.values())

def test_real_earn_balances():
    """Test getting real earn balances"""
    result = get_earn_balances(API_KEY, API_SECRET)
    assert 'account1' in result
    assert 'holdings' in result['account1']

def test_real_spot_trading():
    """Test real spot trading with small amounts"""
    # Buy small amount of BTC with USDT
    buy_result = buy_spot(API_KEY, API_SECRET, "BTC", 10.0)  # Buy $10 worth of BTC
    assert buy_result['status'] == "success"
    assert buy_result['currency'] == "BTC"
    assert buy_result['side'] == "buy"
    assert buy_result['amount'] == 10.0  # Amount in USDT
    
    # Get the bought amount from spot holdings
    holdings = get_spot_holdings(API_KEY, API_SECRET)
    btc_holding = next((h for h in holdings['account1']['holdings'] if h['currency'] == 'BTC'), None)
    assert btc_holding is not None
    
    # Sell the same amount
    if btc_holding:
        sell_result = sell_spot(API_KEY, API_SECRET, "BTC", btc_holding['available'])
        assert sell_result['status'] == "success"
        assert sell_result['currency'] == "BTC"
        assert sell_result['side'] == "sell"
