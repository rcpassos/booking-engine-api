import os
import pytest
from app.config import settings


@pytest.fixture
def api_key_header() -> dict:
    """
    Returns the header dict containing only the required x-api-key.
    """
    return {"x-api-key": settings.api_key}


@pytest.fixture(autouse=True)
def set_test_db_env(monkeypatch):
    # Use the same URI but point at a different database
    monkeypatch.setenv("MONGODB_DB", "booking_test")
    # If you need a separate URI, you could also:
    # monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017/")

    # After the test session ends, you might want to drop this test DB:
    yield
    from pymongo import MongoClient

    client = MongoClient(os.getenv("MONGODB_URI"))
    client.drop_database(os.getenv("MONGODB_DB"))
