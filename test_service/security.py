import os

import jwt
from fastapi import HTTPException, Header

JWT_SECRET = os.environ.get("JWT_SECRET", "testing-expert-system-jwt-secret-2026")
JWT_ALGORITHM = "HS256"

_users_col = None

def _get_users_col():
    # Получение коллекции пользователей
    global _users_col
    if _users_col is None:
        from database import get_col
        get_col()  # ensure connection
        from database import _client
        _users_col = _client["testing_expert"]["users"]
    return _users_col


# Проверка токена и получение текущего пользователя
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
    tv = payload.get("tv", 0)
    try:
        user_doc = _get_users_col().find_one({"username": payload["sub"]}, {"token_version": 1})
        if user_doc and user_doc.get("token_version", 0) != tv:
            raise HTTPException(401, "Token invalidated")
    except HTTPException:
        raise
    except Exception:
        pass
    return payload


# Формирование заголовка авторизации
def get_auth_header(authorization: str) -> dict:
    return {"Authorization": authorization}
