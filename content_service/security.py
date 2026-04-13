import os

import jwt
from fastapi import HTTPException, Header

JWT_SECRET = os.environ.get("JWT_SECRET", "testing-expert-system-jwt-secret-2026")
JWT_ALGORITHM = "HS256"

_users_col = None

def _get_users_col():
    global _users_col
    if _users_col is None:
        from database import get_db
        db = get_db()
        _users_col = db["users"]
    return _users_col


async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")
    try:
        payload = jwt.decode(authorization[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    # Skip tv check for internal service tokens
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
        pass  # DB unavailable — allow request (fail-open for availability)
    return payload
