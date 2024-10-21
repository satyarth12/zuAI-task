from typing import List, Optional

from pydantic import BaseModel, Field


class Params(BaseModel):
    board: str
    grade: int = Field(..., ge=1, le=12)
    subject: str


class Question(BaseModel):
    question: str
    answer: str
    type: str
    question_slug: str
    reference_id: str
    hint: Optional[str] = None
    params: dict = Field(default_factory=dict)


class Section(BaseModel):
    marks_per_question: int = Field(..., gt=0)
    type: str
    questions: List[Question]


class SamplePaper(BaseModel):
    title: str
    type: str
    time: int = Field(..., gt=0)
    marks: int = Field(..., gt=0)
    params: Params
    tags: List[str] = Field(..., min_length=1)
    chapters: List[str] = Field(..., min_length=1)
    sections: List[Section] = Field(..., min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Sample Paper Title",
                "type": "previous_year",
                "time": 180,
                "marks": 100,
                "params": {"board": "CBSE", "grade": 10, "subject": "Maths"},
                "tags": ["algebra", "geometry"],
                "chapters": ["Quadratic Equations", "Triangles"],
                "sections": [
                    {
                        "marks_per_question": 5,
                        "type": "default",
                        "questions": [
                            {
                                "question": "Solve the quadratic equation: x^2 + 5x + 6 = 0",
                                "answer": "The solutions are x = -2 and x = -3",
                                "type": "short",
                                "question_slug": "solve-quadratic-equation",
                                "reference_id": "QE001",
                                "hint": "Use the quadratic formula or factorization method",
                                "params": {},
                            },
                            {
                                "question": "In a right-angled triangle, if one angle is 30°, what is the other acute angle?",
                                "answer": "60°",
                                "type": "short",
                                "question_slug": "right-angle-triangle-angles",
                                "reference_id": "GT001",
                                "hint": "Remember that the sum of angles in a triangle is 180°",
                                "params": {},
                            },
                        ],
                    }
                ],
            }
        }
