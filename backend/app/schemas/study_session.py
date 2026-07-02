import uuid
from datetime import date
from decimal import Decimal

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
    # AGAIN/HARD/GOOD/EASY (Anki-style); PASS/FAIL kept as legacy aliases.
    result: str = Field(pattern="^(AGAIN|HARD|GOOD|EASY|SKIP|PASS|FAIL)$")
    self_note: str | None = None


class NewProgress(CamelModel):
    times_review: int
    passed: bool
    wrong_count: int
    hard_level: str
    next_review_date: date | None
    ease: Decimal = Decimal("2.50")
    interval_days: int = 0


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


class UndoResponse(CamelModel):
    session_item_id: uuid.UUID
    study_item_id: uuid.UUID
    undone_result: str | None
    restored: NewProgress
    session_progress: SessionProgress
