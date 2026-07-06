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


_PROGRESS_DEFAULTS = dict(
    last_date_review=None, next_review_date=None, times_review=0,
    passed=False, wrong_count=0, last_result=None, hard_level="Normal",
)


def merged_out(item, progress=None) -> "StudyItemOut":
    """Catalog item + user progress merged into the SAME response shape the
    app always used — mobile/web need no changes after the catalog split."""
    data = dict(
        id=item.id, language_id=item.language_id, item_type=item.item_type,
        text=item.text, pronunciation=item.pronunciation,
        vietnamese_meaning=item.vietnamese_meaning, example=item.example,
        example_vietnamese=item.example_vietnamese, topic=item.topic,
        situation=item.situation, difficulty=item.difficulty,
        frequency_level=item.frequency_level, notes=item.notes,
        is_archived=item.is_archived,
    )
    if progress is None:
        data.update(_PROGRESS_DEFAULTS)
    else:
        data.update(
            last_date_review=progress.last_date_review,
            next_review_date=progress.next_review_date,
            times_review=progress.times_review,
            passed=progress.passed,
            wrong_count=progress.wrong_count,
            last_result=progress.last_result,
            hard_level=progress.hard_level,
        )
    return StudyItemOut(**data)


class StudyItemPage(CamelModel):
    items: list[StudyItemOut]
    total: int
    page: int
    page_size: int
