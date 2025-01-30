from cryptography.fernet import Fernet
from base64 import b64encode
import streamlit as st

def get_encryption_key():
    """Get or create encryption key"""
    if 'encryption_key' not in st.secrets:
        # Generate new key if not exists
        key = Fernet.generate_key()
        print("WARNING: No encryption key found in secrets. Generated new key:", key.decode())
        print("Add this key to your secrets.toml under [encryption] key = 'YOUR_KEY'")
        return key
    return st.secrets['encryption']['key'].encode()

def encrypt_text(text: str) -> str:
    """Encrypt text using Fernet encryption"""
    try:
        f = Fernet(get_encryption_key())
        return b64encode(f.encrypt(text.encode())).decode()
    except Exception as e:
        print(f"Encryption error: {e}")
        raise

def decrypt_text(encrypted_text: str) -> str:
    """Decrypt text using Fernet encryption"""
    try:
        f = Fernet(get_encryption_key())
        return f.decrypt(b64encode(encrypted_text.encode()).decode().encode()).decode()
    except Exception as e:
        print(f"Decryption error: {e}")
        raise
