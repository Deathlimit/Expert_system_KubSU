from typing import Optional, List, Union

from pydantic import BaseModel


class StartSessionBody(BaseModel):
    test_id: Optional[str] = None
    num_questions_per_category: Optional[dict] = None


class SubmitAnswerBody(BaseModel):
    answer: Union[str, List[str]]
