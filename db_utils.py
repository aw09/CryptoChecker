import pymongo
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional
from crypto_utils import encrypt_text, decrypt_text

client = pymongo.MongoClient(st.secrets["mongodb"]["url"])
db = client.crypto_checker

# Collections
users = db.users
alerts = db.alerts

async def register_user(user_id: int, username: str) -> bool:
    try:
        users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "username": username,
                    "registered_at": datetime.now(),
                    "api_keys": []
                }
            },
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error registering user: {e}")
        return False

async def add_api_key(user_id: int, name: str, api_key: str, api_secret: str) -> bool:
    try:
        # Encrypt sensitive data
        encrypted_key = encrypt_text(api_key)
        encrypted_secret = encrypt_text(api_secret)
        
        users.update_one(
            {"user_id": user_id},
            {
                "$push": {
                    "api_keys": {
                        "name": name,
                        "api_key": encrypted_key,
                        "api_secret": encrypted_secret,
                        "added_at": datetime.now()
                    }
                }
            }
        )
        return True
    except Exception as e:
        print(f"Error adding API key: {e}")
        return False

async def get_user_api_keys(user_id: int, decrypt: bool = False) -> List[Dict]:
    try:
        user = users.find_one({"user_id": user_id})
        if not user:
            return []
            
        api_keys = user.get("api_keys", [])
        if decrypt:
            for api in api_keys:
                api['api_key'] = decrypt_text(api['api_key'])
                api['api_secret'] = decrypt_text(api['api_secret'])
        return api_keys
    except Exception as e:
        print(f"Error getting API keys: {e}")
        return []

async def delete_api_key(user_id: int, api_name: str) -> bool:
    try:
        result = users.update_one(
            {"user_id": user_id},
            {"$pull": {"api_keys": {"name": api_name}}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error deleting API key: {e}")
        return False

async def set_alert(user_id: int, coin: str, condition: str, price: float) -> bool:
    try:
        alerts.insert_one({
            "user_id": user_id,
            "coin": coin.upper(),
            "condition": condition,  # ">" or "<"
            "price": price,
            "created_at": datetime.now(),
            "active": True
        })
        return True
    except Exception as e:
        print(f"Error setting alert: {e}")
        return False

async def get_user_alerts(user_id: int) -> List[Dict]:
    try:
        return list(alerts.find({"user_id": user_id, "active": True}))
    except Exception as e:
        print(f"Error getting alerts: {e}")
        return []
