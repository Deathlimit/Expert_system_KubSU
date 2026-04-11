from typing import List, Optional

from pydantic import BaseModel, Field


class CreateTestBody(BaseModel):
    test_name: str = Field(..., min_length=1, max_length=300)
    questions: List[dict] = Field(..., min_length=1)
    time_limit_minutes: Optional[int] = Field(default=None, ge=1)
    cooldown_hours: Optional[int] = Field(default=24, ge=0)
    max_attempts: Optional[int] = Field(default=None, ge=1)


class AssignBody(BaseModel):
    student_username: str = Field(..., min_length=1)


class BatchAssignBody(BaseModel):
    assign: List[str] = []
    unassign: List[str] = []


class GenerateTestBody(BaseModel):
    topic: str = Field(..., min_length=1)
    max_score: int = Field(..., ge=1)


class AddQuestionsBody(BaseModel):
    questions: List[dict] = Field(..., min_length=1)


class RenameTestBody(BaseModel):
    test_name: str = Field(..., min_length=1, max_length=300)
