import uuid
from datetime import date

from pydantic import Field

from app.schemas.common import CamelModel
from app.schemas.study_item import StudyItemOut


class SessionItemOut(CamelModel):
    id: uuid.UUID  # session item id
    position: int
    planned_bucket: str
    result: str | None
    item: StudyItemOut


class SessionOut(CamelModel):
    id: uuid.UUID
    language_id: uuid.UUID | None
    session_type: str
    status: str
    study_date: date
    total_items: int
    completed_items: int
    pass_count: int
    fail_count: int
    skip_count: int
    items: list[SessionItemOut] = []


class ReviewRequest(CamelModel):
    result: str = Field(pattern="^(PASS|FAIL|SKIP)$")
    self_note: str | None = None


class NewProgress(CamelModel):
    times_review: int
    passed: bool
    wrong_count: int
    hard_level: str
    next_review_date: date | None


class SessionProgress(CamelModel):
    completed_items: int
    total_items: int
    pass_count: int
    fail_count: int
    skip_count: int


class ReviewResponse(CamelModel):
    session_item_id: uuid.UUID
    study_item_id: uuid.UUID
    result: str
    already_applied: bool = False
    new_progress: NewProgress
    session_progress: SessionProgress
