import logging
import os
from typing import Optional

from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://admin:admin123@localhost:27017/testing_expert?authSource=admin")
CONTENT_SERVICE_URL = os.environ.get("CONTENT_SERVICE_URL", "http://localhost:8002")
TEST_SERVICE_URL = os.environ.get("TEST_SERVICE_URL", "http://localhost:8003")

_client: Optional[MongoClient] = None


def get_col():
    global _client
    if _client is None:
        try:
            _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            _client.admin.command("ping")
            logger.info("Connected to MongoDB.")
        except ConnectionFailure as e:
            logger.error("Failed to connect to MongoDB: %s", e)
            _client = None
            raise RuntimeError(f"Database connection failed: {e}")
        _client["testing_expert"]["test_results"].create_index([("username", 1), ("premade_test_id", 1)])
        _client["testing_expert"]["test_results"].create_index([("end_time", DESCENDING)])
    return _client["testing_expert"]["test_results"]


def get_active_sessions_col():
    # Возвращает коллекцию активных сессий
    global _client
    if _client is None:
        get_col()  # ensure connection
    col = _client["testing_expert"]["active_sessions"]
    col.create_index("session_id", unique=True)
    col.create_index("username")
    return col
