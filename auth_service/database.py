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

DEMO_TEST_ID = "demo_test_intro"

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


def get_tests_col():
    """Return the 'premade_tests' collection (shared with test_service)."""
    get_db()  # ensure connection
    return _client["testing_expert"]["premade_tests"]


def ensure_demo_test():
    """Create the introductory demo test if it doesn't exist."""
    from datetime import datetime, timezone as tz
    col = get_tests_col()
    if col.find_one({"test_id": DEMO_TEST_ID}):
        return
    demo_questions = [
        {
            "question": "Какая планета ближайшая к Солнцу?",
            "options": ["Венера", "Меркурий", "Земля", "Марс"],
            "correct": "Меркурий",
            "answer_type": "single",
            "category": "Демонстрация",
            "points": 1,
        },
        {
            "question": "Выберите языки программирования из списка:",
            "options": ["Python", "HTML", "Java", "CSS"],
            "correct": ["Python", "Java"],
            "answer_type": "multiple",
            "category": "Демонстрация",
            "points": 2,
        },
        {
            "question": "Сколько будет 2 + 2?",
            "options": ["3", "4", "5", "22"],
            "correct": "4",
            "answer_type": "single",
            "category": "Демонстрация",
            "points": 1,
        },
    ]
    col.insert_one({
        "test_id": DEMO_TEST_ID,
        "test_name": "Начало. Ознакомление с системой",
        "creator_username": "__system__",
        "creation_date": datetime.now(tz.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "questions": demo_questions,
        "assigned_students": [],
        "time_limit_minutes": None,
        "cooldown_hours": 0,
        "max_attempts": None,
    })
    logger.info("Demo test created.")
