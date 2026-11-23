"""Модели запросов сервиса очереди."""

from typing import Any, Optional

from pydantic import BaseModel, Field

DEFAULT_TASK_TYPE = "create_student_profile"


class CreateTaskBody(BaseModel):
    type: str = Field(default=DEFAULT_TASK_TYPE, max_length=100)
    username: Optional[str] = Field(default=None, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    # Пересоздать задачу, даже если для пользователя уже есть активная.
    force: bool = Field(default=False)