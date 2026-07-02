import uuid
from datetime import date

from pydantic import Field

from app.schemas.common import CamelModel

ITEM_TYPES = ("VOCABULARY", "SENTENCE")


class StudyItemCreate(CamelModel):
    language_id: uuid.UUID
    item_type: str = Field(pattern="^(VOCABULARY|SENTENCE)$")
    text: str = Field(min_length=1)
    pronunciation: str | None = None
    vietnamese_meaning: str | None = None
    example: str | None = None
    example_vietnamese: str | None = None
    topic: str | None = Field(default=None, max_length=120)
    situation: str | None = Field(default=None, max_length=120)
    difficulty: str | None = Field(default=None, max_length=40)
    frequency_level: str | None = Field(default=None, max_length=40)
    notes: str | None = None
    source: str | None = Field(default=None, max_length=120)


class StudyItemUpdate(CamelModel):
    text: str | None = Field(default=None, min_length=1)
    pronunciation: str | None = None
    vietnamese_meaning: str | None = None
    example: str | None = None
    example_vietnamese: str | None = None
    topic: str | None = Field(default=None, max_length=120)
    situation: str | None = Field(default=None, max_length=120)
    difficulty: str | None = Field(default=None, max_length=40)
    frequency_level: str | None = Field(default=None, max_length=40)
    notes: str | None = None
    is_archived: bool | None = None


class StudyItemOut(CamelModel):
    id: uuid.UUID
    language_id: uuid.UUID
    item_type: str
    text: str
    pronunciation: str | None
    vietnamese_meaning: str | None
    example: str | None
    example_vietnamese: str | None
    topic: str | None
    situation: str | None
    difficulty: str | None
    frequency_level: str | None
    notes: str | None
    last_date_review: date | None
    next_review_date: date | None
    times_review: int
    passed: bool
    wrong_count: int
    last_result: str | None
    hard_level: str
    is_archived: bool


class StudyItemPage(CamelModel):
    items: list[StudyItemOut]
    total: int
    page: int
    page_size: int
