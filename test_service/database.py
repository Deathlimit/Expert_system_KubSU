import logging
import os
from typing import Optional

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://admin:admin123@localhost:27017/testing_expert?authSource=admin")
CONTENT_SERVICE_URL = os.environ.get("CONTENT_SERVICE_URL", "http://localhost:8002")

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
        _client["testing_expert"]["premade_tests"].create_index("test_id", unique=True)
        _client["testing_expert"]["premade_tests"].create_index("share_token", sparse=True, unique=True)
    return _client["testing_expert"]["premade_tests"]


def get_users_col():
    # Получение коллекции пользователей
    get_col()
    return _client["testing_expert"]["users"]


def clean(doc: dict) -> dict:
    # Удаление _id из документа
    doc.pop("_id", None)
    return doc
