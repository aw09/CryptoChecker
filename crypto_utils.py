from cryptography.fernet import Fernet
import base64
import streamlit as st

def get_encryption_key():
    """Get or create encryption key"""
    if 'encryption' not in st.secrets or 'key' not in st.secrets['encryption']:
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
        encrypted_data = f.encrypt(text.encode())
        return base64.b64encode(encrypted_data).decode()
    except Exception as e:
        print(f"Encryption error: {e}")
        raise

def decrypt_text(encrypted_text: str) -> str:
    """Decrypt text using Fernet encryption"""
    try:
        f = Fernet(get_encryption_key())
        decoded_data = base64.b64decode(encrypted_text)
        return f.decrypt(decoded_data).decode()
    except Exception as e:
        print(f"Decryption error: {e}")
        raise
