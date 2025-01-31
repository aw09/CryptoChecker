import gate_api
import streamlit as st
import logging

# Configure logger
logger = logging.getLogger(__name__)

def get_client(api_key: str, api_secret: str, name: str = "Selected Account"):
    """Create a single Gate.io client with given credentials"""
    try:
        configuration = gate_api.Configuration(
            key=api_key,
            secret=api_secret
        )
        return {
            "client": gate_api.ApiClient(configuration),
            "name": name
        }
    except Exception as e:
        logger.error(f"Error creating Gate.io client: {str(e)}")
        raise

def check_ticker_exists(api_key: str, api_secret: str, currency: str) -> bool:
    """Check if a ticker exists for the given currency"""
    try:
        client_data = get_client(api_key, api_secret)
        spot_api = gate_api.SpotApi(client_data["client"])
        ticker = spot_api.list_tickers(currency_pair=f"{currency}_USDT")
        return len(ticker) > 0 and float(ticker[0].last) > 0
    except Exception as e:
        logger.error(f"Error checking ticker: {e}")
        return False

def get_balance(api_key: str = None, api_secret: str = None):
    try:
        if api_key and api_secret:
            client_data = get_client(api_key, api_secret)
            wallet_api = gate_api.WalletApi(client_data["client"])
            balance = float(wallet_api.get_total_balance().total.amount)
            
            return {
                "account1": {
                    "name": client_data["name"],
                    "balance": balance
                },
                "total": balance
            }
        else:
            logger.error("No API credentials provided")
            raise ValueError("API credentials are required")
            
    except Exception as e:
        logger.error(f"Gate.io API error: {str(e)}")
        raise

def get_usdt_price(spot_api, currency):
    if currency == 'USDT':
        return 1.0
    try:
        ticker = spot_api.list_tickers(currency_pair=f"{currency}_USDT")
        return float(ticker[0].last)
    except:
        return 0.0

def get_spot_holdings(api_key: str = None, api_secret: str = None, min_usdt_value=0.5):
    try:
        if not api_key or not api_secret:
            raise ValueError("API credentials are required")
            
        client_data = get_client(api_key, api_secret)
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
        
        return {
            "account1": {
                "name": client_data["name"],
                "holdings": sorted(holdings, key=lambda x: x['value_usdt'], reverse=True)
            }
        }
            
    except Exception as e:
        logger.error(f"Gate.io API error: {str(e)}")
        raise

def check_current_price(api_key, api_secret, coin):
    """Get current price for a coin"""
    try:
        client_data = get_client(api_key, api_secret)
        spot_api = gate_api.SpotApi(client_data["client"])
        ticker = spot_api.list_tickers(currency_pair=f"{coin}_USDT")
        if ticker and len(ticker) > 0:
            return float(ticker[0].last)
        raise ValueError(f"No ticker found for {coin}_USDT")
    except Exception as e:
        logger.error(f"Error getting price for {coin}: {e}")
        raise

def get_multiple_prices(api_key: str, api_secret: str, coins: list) -> dict:
    """Get prices for multiple coins in a single batch"""
    try:
        client_data = get_client(api_key, api_secret)
        spot_api = gate_api.SpotApi(client_data["client"])
        
        # Get all USDT pairs in one request
        all_tickers = spot_api.list_tickers()
        
        # Create price lookup dictionary
        prices = {}
        for ticker in all_tickers:
            # Parse currency from pair (e.g., "BTC_USDT" -> "BTC")
            if ticker.currency_pair.endswith('_USDT'):
                currency = ticker.currency_pair[:-5]  # Remove _USDT
                if currency in coins:
                    prices[currency] = float(ticker.last)
        
        return prices
        
    except Exception as e:
        logger.error(f"Error getting multiple prices: {e}")
        raise

def get_earn_balances(api_key: str = None, api_secret: str = None):
    """Get balances from Gate.io Earn products"""
    try:
        if not api_key or not api_secret:
            raise ValueError("API credentials are required")
            
        client_data = get_client(api_key, api_secret)
        earn_uni_api = gate_api.EarnUniApi(client_data["client"])
        spot_api = gate_api.SpotApi(client_data["client"])
        
        # Get all earn positions using the correct method name
        earn_uni_records = earn_uni_api.list_user_uni_lends()
        holdings = []
        
        for record in earn_uni_records:
            amount = float(record.amount)
            if amount > 0:
                # Get current USDT price for the currency
                price = get_usdt_price(spot_api, record.currency)
                usdt_value = amount * price
                
                holdings.append({
                    "currency": record.currency,
                    "amount": amount,
                    "frozen_amount": float(record.frozen_amount),
                    "interest_status": record.interest_status,
                    "min_rate": float(record.min_rate),
                    "create_time": record.create_time,
                    "update_time": record.update_time,
                    "price_usdt": price,
                    "value_usdt": usdt_value
                })
        
        return {
            "account1": {
                "name": client_data["name"],
                "holdings": sorted(holdings, key=lambda x: x['value_usdt'], reverse=True)
            }
        }
            
    except Exception as e:
        logger.error(f"Gate.io Earn API error: {str(e)}")
        raise

def get_lending_rates(api_key: str = None, api_secret: str = None):
    """Get available lending rates for all currencies"""
    try:
        if not api_key or not api_secret:
            raise ValueError("API credentials are required")
            
        client_data = get_client(api_key, api_secret)
        earn_uni_api = gate_api.EarnUniApi(client_data["client"])
        
        # Get lending market info
        lending_currencies = earn_uni_api.list_uni_currencies()
        rates = {}
        
        for currency in lending_currencies:
            rates[currency.currency] = {
                "min_rate": float(currency.min_rate),
                "max_rate": float(currency.max_rate),
                "min_amount": float(currency.min_lend_amount),
                "max_amount": float(currency.max_lend_amount)
            }
        
        return rates
            
    except Exception as e:
        logger.error(f"Gate.io Earn API error: {str(e)}")
        raise

def lend_to_earn(api_key: str, api_secret: str, currency: str, amount: float, min_rate: float = None):
    """Lend funds to Gate.io Earn products"""
    try:
        if not api_key or not api_secret:
            raise ValueError("API credentials are required")
            
        client_data = get_client(api_key, api_secret)
        earn_uni_api = gate_api.EarnUniApi(client_data["client"])
        
        # If min_rate not provided, get it from lending rates
        if min_rate is None:
            rates = get_lending_rates(api_key, api_secret)
            if currency not in rates:
                raise ValueError(f"Currency {currency} not available for lending")
            min_rate = rates[currency]['min_rate']
        
        # Format min_rate as decimal string
        formatted_min_rate = "{:.8f}".format(min_rate)
        
        # Create lending request
        lend_request = gate_api.CreateUniLend(
            currency=currency,
            amount=str(amount),
            min_rate=formatted_min_rate,
            type='lend'
        )
        
        # Submit lending request
        result = earn_uni_api.create_uni_lend(lend_request)
        
        return {
            "status": "success",
            "currency": currency,
            "amount": amount,
            "min_rate": min_rate
        }
            
    except Exception as e:
        logger.error(f"Gate.io Earn lending error: {str(e)}")
        raise

def redeem_from_earn(api_key: str, api_secret: str, currency: str, amount: float = None, redeem_all: bool = False):
    """Redeem funds from Gate.io Earn products"""
    try:
        if not api_key or not api_secret:
            raise ValueError("API credentials are required")
            
        client_data = get_client(api_key, api_secret)
        earn_uni_api = gate_api.EarnUniApi(client_data["client"])
        
        # If redeem_all is True, get current earn balance
        if redeem_all:
            earn_records = earn_uni_api.list_user_uni_lends()
            for record in earn_records:
                if record.currency == currency:
                    amount = float(record.amount)
                    break
            if not amount:
                raise ValueError(f"No balance found for {currency} in earn")
        elif amount is None:
            raise ValueError("Must specify amount or set redeem_all=True")
        
        # Create redemption request
        redeem_request = gate_api.CreateUniLend(
            currency=currency,
            amount=str(amount),
            type='redeem'
        )
        
        # Submit redemption request - API returns None on success
        earn_uni_api.create_uni_lend(redeem_request)
        
        # Return success response without order_id and create_time
        return {
            "status": "success",
            "currency": currency,
            "amount": amount
        }
            
    except Exception as e:
        logger.error(f"Gate.io Earn redemption error: {str(e)}")
        raise

# Update the main block to test the new functionality
if __name__ == '__main__':
    from dotenv import load_dotenv
    import os

    load_dotenv()

    API_KEY = os.getenv('GATE_API_KEY')
    API_SECRET = os.getenv('GATE_API_SECRET')

    try:
        # Check earn balances before redemption
        balances = get_earn_balances(API_KEY, API_SECRET)
        print("Earn balances:", balances)

        # Test redeeming all BTC from earn
        result = redeem_from_earn(API_KEY, API_SECRET, "BTC", redeem_all=True)
        print("Redemption result:", result)
        
        # Check updated earn balances after redemption
        balances = get_earn_balances(API_KEY, API_SECRET)
        print("\nUpdated earn balances:", balances)
        
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Redemption error: {str(e)}")

