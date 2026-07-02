import uuid
from decimal import Decimal

from pydantic import Field, model_validator

from app.schemas.common import CamelModel


class LanguageCreate(CamelModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=80)
    native_name: str | None = Field(default=None, max_length=120)
    tts_lang: str = Field(min_length=2, max_length=20)
    accent_color: str | None = Field(default=None, max_length=20)
    sort_order: int = 0


class LanguageUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    native_name: str | None = Field(default=None, max_length=120)
    tts_lang: str | None = Field(default=None, min_length=2, max_length=20)
    accent_color: str | None = Field(default=None, max_length=20)
    sort_order: int | None = None
    is_active: bool | None = None


class LanguageOut(CamelModel):
    id: uuid.UUID
    code: str
    name: str
    native_name: str | None
    tts_lang: str
    accent_color: str | None
    sort_order: int
    is_active: bool


class LanguageSettingUpdate(CamelModel):
    """All optional; validation per spec §13.2."""

    daily_limit: int | None = Field(default=None, ge=1, le=200)
    vocabulary_ratio: Decimal | None = Field(default=None, ge=0, le=1)
    sentence_ratio: Decimal | None = Field(default=None, ge=0, le=1)
    new_ratio: Decimal | None = Field(default=None, ge=0, le=1)
    review_ratio: Decimal | None = Field(default=None, ge=0, le=1)
    times_limit: int | None = Field(default=None, ge=1, le=20)
    sentence_times_limit: int | None = Field(default=None, ge=1, le=20)
    review_intervals: list[int] | None = None
    sentence_review_intervals: list[int] | None = None
    difficulty_filter: list[str] | None = None
    sentence_difficulty_filter: list[str] | None = None
    topic_filter: list[str] | None = None
    situation_filter: list[str] | None = None
    frequency_filter: list[str] | None = None
    include_passed_items: bool | None = None
    passed_review_after_days: int | None = Field(default=None, ge=1)
    reset_on_fail: bool | None = None
    avoid_same_day_repeat: bool | None = None
    sort_mode: str | None = None
    item_ordering: str | None = None
    study_direction: str | None = Field(
        default=None, pattern="^(FRONT|REVERSE|LISTENING|MIXED)$")

    @model_validator(mode="after")
    def validate_ratios_and_intervals(self):
        def _pair_sums_to_one(a, b, names):
            if a is not None and b is not None and a + b != 1:
                raise ValueError(f"{names} must sum to 1")
            if (a is None) != (b is None):
                raise ValueError(f"Provide both of {names} together")

        _pair_sums_to_one(self.vocabulary_ratio, self.sentence_ratio,
                          "vocabularyRatio + sentenceRatio")
        _pair_sums_to_one(self.new_ratio, self.review_ratio, "newRatio + reviewRatio")
        for field in (self.review_intervals, self.sentence_review_intervals):
            if field is not None:
                if not field or any(i < 1 for i in field):
                    raise ValueError("Review intervals must be positive integers")
        return self


class LanguageSettingOut(CamelModel):
    id: uuid.UUID
    language_id: uuid.UUID
    daily_limit: int
    vocabulary_ratio: Decimal
    sentence_ratio: Decimal
    new_ratio: Decimal
    review_ratio: Decimal
    times_limit: int
    sentence_times_limit: int
    review_intervals: list[int]
    sentence_review_intervals: list[int]
    difficulty_filter: list[str]
    sentence_difficulty_filter: list[str]
    topic_filter: list[str]
    situation_filter: list[str]
    frequency_filter: list[str]
    include_passed_items: bool
    passed_review_after_days: int
    reset_on_fail: bool
    avoid_same_day_repeat: bool
    sort_mode: str
    item_ordering: str
    study_direction: str
    is_active: bool
