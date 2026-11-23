from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Zа-яА-ЯёЁ0-9_.\-]+$")
    password: str = Field(..., min_length=6, max_length=200)
    full_name: str = Field(default="", max_length=200)
    group: Optional[str] = Field(default="", max_length=50)


class ChangeRoleRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=20)


class ChangeGroupRequest(BaseModel):
    group: Optional[str] = Field(default="", max_length=50)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=6, max_length=200)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=200)


class UpdateFullNameRequest(BaseModel):
    full_name: str = Field(..., min_length=0, max_length=200)


class GroupBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
