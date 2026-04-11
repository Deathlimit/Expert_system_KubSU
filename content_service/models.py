from typing import Optional, List, Union

from pydantic import BaseModel, Field


class QuestionBody(BaseModel):
    question: str = Field(..., min_length=1)
    options: List[str] = Field(..., min_length=1)
    correct: Union[str, List[str]]
    answer_type: Optional[str] = "single"
    points: Optional[int] = Field(default=None, ge=1)
    category: Optional[str] = None
    matrices: Optional[dict] = None
    commands: Optional[dict] = None


class CriteriaBody(BaseModel):
    topic_criteria: List[dict] = Field(..., min_length=1)


class BulkImportBody(BaseModel):
    questions: List[dict] = Field(..., min_length=1)
