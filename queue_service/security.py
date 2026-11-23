"""Аутентификация пользователя и воркера для сервиса очереди."""

import os
import secrets

import jwt
from fastapi import Header, HTTPException

from .database import get_users_col

JWT_SECRET = os.environ.get("JWT_SECRET", "testing-expert-system-jwt-secret-2026")
JWT_ALGORITHM = "HS256"
# Пусто — воркер может опрашивать очередь без токена (локальная разработка).
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "").strip()


async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if payload.get("sub", "").startswith("__service__"):
        return payload
    try:
        user_doc = get_users_col().find_one({"username": payload["sub"]}, {"token_version": 1})
        if user_doc and user_doc.get("token_version", 0) != payload.get("tv", 0):
            raise HTTPException(401, "Token invalidated")
    except HTTPException:
        raise
    except Exception:
        pass
    return payload


async def verify_worker(x_worker_token: str = Header(default="")):
    """Проверяет X-Worker-Token, если WORKER_TOKEN задан в окружении.

    Номер задачи — случайный секрет, поэтому без токена перебирать очередь
    нецелесообразно; токен всё равно рекомендуется задать в production.
    """
    if not WORKER_TOKEN:
        return
    if not secrets.compare_digest(x_worker_token or "", WORKER_TOKEN):
        raise HTTPException(401, "Неверный X-Worker-Token.")