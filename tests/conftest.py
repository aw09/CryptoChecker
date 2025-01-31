import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import streamlit as st

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_db():
    """Create a test database connection."""
    client = AsyncIOMotorClient(st.secrets["mongodb"]["url"])
    db = client.crypto_checker_test
    return db

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
