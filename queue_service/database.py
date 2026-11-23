"""Mongo-хранилище очереди задач и профилей студентов."""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from pymongo import ASCENDING, MongoClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)

MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb://admin:admin123@localhost:27017/testing_expert?authSource=admin",
)
# Сколько задание может висеть в in_progress, прежде чем вернётся в очередь.
LEASE_SECONDS = int(os.environ.get("QUEUE_LEASE_SECONDS", "600"))
# 0 — хранить задания бессрочно. Иначе — TTL по finished_at.
TASK_TTL_SECONDS = int(os.environ.get("QUEUE_TASK_TTL_SECONDS", "0"))

_client: Optional[MongoClient] = None


def _get_client() -> MongoClient:
    global _client
    if _client is None:
        try:
            _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            _client.admin.command("ping")
            logger.info("Queue Service connected to MongoDB.")
        except ConnectionFailure as e:
            logger.error("Queue Service failed to connect to MongoDB: %s", e)
            _client = None
            raise RuntimeError(f"Database connection failed: {e}")
    return _client


def get_db():
    return _get_client()["testing_expert"]


def get_tasks_col():
    col = get_db()["queue_tasks"]
    col.create_index("status")
    col.create_index([("type", ASCENDING), ("status", ASCENDING)])
    col.create_index("username")
    col.create_index("created_at")
    if TASK_TTL_SECONDS > 0:
        col.create_index("finished_at", expireAfterSeconds=TASK_TTL_SECONDS)
    return col


def get_profiles_col():
    """Сохранённые результаты задач «создать профиль студента»."""
    col = get_db()["student_profiles"]
    col.create_index("username", unique=True)
    return col


def get_portraits_col():
    """Совместимость: результат задачи дублируется и сюда, чтобы профиль
    можно было прочитать напрямую из student_portraits."""
    col = get_db()["student_portraits"]
    col.create_index("username", unique=True)
    return col


def get_users_col():
    return get_db()["users"]


def get_results_col():
    """Результаты тестов — входные данные для создания профиля."""
    col = get_db()["test_results"]
    col.create_index("username")
    return col


def now_utc() -> datetime:
    return datetime.now(timezone.utc)