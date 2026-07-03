import uuid
from datetime import date

from app.schemas.common import CamelModel


class TodaySummary(CamelModel):
    today_learned: int
    pass_count: int
    fail_count: int
    skip_count: int
    pass_rate: float  # 0..1, over pass+fail (skips excluded)
    streak_days: int
    due_today: int
    hard_items_count: int


class LanguageSummary(CamelModel):
    language_id: uuid.UUID
    code: str
    name: str
    accent_color: str | None
    tts_lang: str
    due_count: int
    new_count: int
    vocab_due_new: int
    sentence_due_new: int
    today_learned: int
    daily_limit: int
    weekly_review_day: str = "SUNDAY"
    # Forecast: cards that become due tomorrow (today's leftovers roll over too).
    due_tomorrow: int = 0
    # Session type (LANGUAGE_DAILY/EXTRA/WEEKLY) of today's unfinished session, if any.
    active_session_type: str | None = None


class HistoryDay(CamelModel):
    day: date
    learned: int
    pass_count: int
    fail_count: int
    skip_count: int
