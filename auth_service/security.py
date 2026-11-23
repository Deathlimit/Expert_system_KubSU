import os
import hashlib
import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, Header

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "testing-expert-system-jwt-secret-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    if len(hashed) == 64:
        try:
            int(hashed, 16)
            return hashlib.sha256(password.encode()).hexdigest() == hashed
        except ValueError:
            pass
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def create_token(username: str, role: str, token_version: int = 0) -> str:
    payload = {
        "sub": username,
        "role": role,
        "tv": token_version,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# Проверка JWT токена
def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


# Получение текущего пользователя из токена
async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")
    return verify_token(authorization[7:])
