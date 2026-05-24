import logging
import os
from typing import Optional

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://admin:admin123@localhost:27017/testing_expert?authSource=admin")

DEFAULT_CRITERIA_KEY = "__default__"
DEFAULT_GRADING_CRITERIA = {
    "topic_criteria": [
        {"threshold_gte": 80, "description": "зачтено", "is_pass_status": True},
        {"threshold_gte": 50, "description": "удовлетворительно", "is_pass_status": True},
        {"threshold_gte": 0, "description": "незачтено", "is_pass_status": False},
    ]
}

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
        db = _client["testing_expert"]
        db["questions"].create_index("topic")
        db["criteria"].create_index("key", unique=True)
    return _client["testing_expert"]


def get_questions_dict(db) -> dict:
    # Возвращает вопросы, сгруппированные по темам
    result: dict = {}
    for doc in db["questions"].find({}, {"_id": 0}):
        topic = doc.get("topic", "unknown")
        if topic not in result:
            result[topic] = []
        result[topic].append({k: v for k, v in doc.items() if k != "topic"})
    return result


def get_criteria(db, key: str) -> Optional[dict]:
    # Получение критериев оценивания по ключу
    doc = db["criteria"].find_one({"key": key}, {"_id": 0, "key": 0})
    if doc and isinstance(doc.get("topic_criteria"), list):
        return doc
    return None
