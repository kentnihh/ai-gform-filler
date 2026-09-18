from enum import Enum
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field

class QuestionType(str, Enum):
    SHORT_ANSWER = "short_answer"
    PARAGRAPH = "paragraph"
    MULTIPLE_CHOICE = "multiple_choice"
    CHECKBOXES = "checkboxes"
    DROPDOWN = "dropdown"
    LINEAR_SCALE = "linear_scale"

class Question(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    type: QuestionType
    required: bool = False
    options: List[str] = Field(default_factory=list)

class Persona(BaseModel):
    age: int
    gender: str
    occupation: str
    usage_frequency: str
    attitude_trait: str

class RespondentData(BaseModel):
    respondent_id: int
    persona: Persona
    answers: Dict[str, Union[str, List[str]]]  # key: question.id, value: answer(s)