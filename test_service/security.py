import os

import jwt
from fastapi import HTTPException, Header

JWT_SECRET = os.environ.get("JWT_SECRET", "testing-expert-system-jwt-secret-2026")
JWT_ALGORITHM = "HS256"


async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")
    try:
        return jwt.decode(authorization[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


def get_auth_header(authorization: str) -> dict:
    return {"Authorization": authorization}
