import logging
import os
from typing import Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://admin:admin123@localhost:27017/testing_expert?authSource=admin")

ROLE_ADMIN = "admin"
ROLE_TEACHER = "teacher"
ROLE_STUDENT = "student"
ROLE_UNASSIGNED = "unassigned"

_client: Optional[MongoClient] = None


def get_db():
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
        _client["testing_expert"]["users"].create_index("username", unique=True)
    return _client["testing_expert"]["users"]


def get_groups_col():
    """Return the 'groups' collection (admin-managed groups)."""
    get_db()  # ensure connection is established
    col = _client["testing_expert"]["groups"]
    col.create_index("name", unique=True)
    return col
