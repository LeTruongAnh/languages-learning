"""Review submission + undo (spec 8, 12.3, 12.4 — upgraded to simplified SM-2).

Grades (Anki-style), with legacy aliases so old clients keep working:
    AGAIN (quen)  <- FAIL     : reset progress, wrong+1, ease -0.20, next = +1d
    HARD  (kho)               : advance, ease -0.15, interval x1.2
    GOOD  (nho)   <- PASS     : advance, ease same,  interval x ease
    EASY  (de)                : advance, ease +0.15, interval x ease x1.3
    SKIP                      : log only, no progress change

First successful review (no previous interval) uses the per-language base
intervals list; EASY doubles it. Ease is clamped to [1.30, 3.00].
Graduation unchanged: passed when times_review >= times_limit.

One transaction per submit; idempotent via session_item.applied_at.
Undo (Anki-style, single step): only the most recently answered card of an
ACTIVE session can be undone — restores the item from the review_log snapshot,
decrements session counters, deletes the log row.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.timeutil import today_in_tz
from app.models import ReviewLog, StudyItem, StudySessionItem
from app.schemas.study_session import (
    NewProgress,
    ReviewResponse,
    SessionProgress,
    UndoResponse,
)
from app.services.language_service import get_settings
from app.services.study_session_service import get_session
from app.services.user_service import get_user_timezone

GRADE_ALIASES = {"PASS": "GOOD", "FAIL": "AGAIN"}
REMEMBER_GRADES = ("HARD", "GOOD", "EASY")

EASE_MIN = 1.30
EASE_MAX = 3.00
EASE_DELTA = {"AGAIN": -0.20, "HARD": -0.15, "GOOD": 0.0, "EASY": +0.15}


def compute_hard_level(wrong_count: int) -> str:
    """Spec 8.2."""
    if wrong_count >= 3:
        return "Very Hard"
    if wrong_count >= 2:
        return "Hard"
    return "Normal"


def next_interval_days(intervals: list[int], times_review: int) -> int:
    """Base interval from settings list, clamped to the last entry."""
    if not intervals:
        return 1
    index = min(times_review, len(intervals)) - 1
    return intervals[max(index, 0)]


def apply_ease(old_ease: float, grade: str) -> float:
    return round(min(EASE_MAX, max(EASE_MIN, old_ease + EASE_DELTA[grade])), 2)


def compute_interval(
    grade: str, prev_interval: int, ease: float, times_review_new: int, intervals: list[int]
) -> int:
    """Next interval in days for a remembered card (HARD/GOOD/EASY)."""
    if prev_interval <= 0:
        base = next_interval_days(intervals, times_review_new)
        return base * 2 if grade == "EASY" else base
    if grade == "HARD":
        return max(1, round(prev_interval * 1.2))
    if grade == "EASY":
        return max(prev_interval + 2, round(prev_interval * ease * 1.3))
    return max(prev_interval + 1, round(prev_interval * ease))  # GOOD


async def submit_review(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    session_item_id: uuid.UUID,
    result: str,
    self_note: str | None = None,
) -> ReviewResponse:
    grade = GRADE_ALIASES.get(result, result)

    session = await get_session(db, user_id, session_id)  # ownership -> 404
    if session.status != "ACTIVE":
        raise ConflictError(f"Session is {session.status}")

    session_item = await db.scalar(
        select(StudySessionItem).where(
            StudySessionItem.id == session_item_id,
            StudySessionItem.session_id == session.id,
        )
    )
    if session_item is None:
        raise NotFoundError("Session item")

    item = await db.scalar(
        select(StudyItem).where(
            StudyItem.id == session_item.study_item_id, StudyItem.user_id == user_id
        )
    )
    if item is None:
        raise NotFoundError("Study item")

    # Idempotency (spec 12.4): already applied -> return stored state.
    if session_item.applied_at is not None:
        return _build_response(session, session_item, item, already_applied=True)

    settings = await get_settings(db, user_id, item.language_id)
    today = today_in_tz(await get_user_timezone(db, user_id))

    old = dict(
        times_review=item.times_review,
        passed=item.passed,
        wrong_count=item.wrong_count,
        hard_level=item.hard_level,
        next_review_date=item.next_review_date,
        ease=item.ease,
        interval_days=item.interval_days,
        last_result=item.last_result,
        last_date_review=item.last_date_review,
    )

    if item.item_type == "SENTENCE":
        times_limit = settings.sentence_times_limit
        intervals = settings.sentence_review_intervals
    else:
        times_limit = settings.times_limit
        intervals = settings.review_intervals

    if grade == "AGAIN":
        item.times_review = 0 if settings.reset_on_fail else item.times_review
        item.passed = False
        item.wrong_count = item.wrong_count + 1
        item.hard_level = compute_hard_level(item.wrong_count)
        item.ease = Decimal(str(apply_ease(float(item.ease), grade)))
        item.interval_days = 1
        item.next_review_date = today + timedelta(days=1)
        item.last_result = grade
        item.last_date_review = today
    elif grade in REMEMBER_GRADES:
        item.times_review = item.times_review + 1
        item.passed = item.times_review >= times_limit
        item.hard_level = compute_hard_level(item.wrong_count)
        new_ease = apply_ease(float(item.ease), grade)
        item.ease = Decimal(str(new_ease))
        if item.passed:
            item.interval_days = 0
            item.next_review_date = None  # retired (spec 8.1)
        else:
            item.interval_days = compute_interval(
                grade, old["interval_days"], new_ease, item.times_review, intervals
            )
            item.next_review_date = today + timedelta(days=item.interval_days)
        item.last_result = grade
        item.last_date_review = today
    # SKIP: no progress changes (spec 8.1)

    session_item.result = grade
    session_item.applied_at = datetime.now(timezone.utc)

    session.completed_items += 1
    if grade in REMEMBER_GRADES:
        session.pass_count += 1
    elif grade == "AGAIN":
        session.fail_count += 1
    else:
        session.skip_count += 1

    db.add(ReviewLog(
        user_id=user_id,
        language_id=item.language_id,
        session_id=session.id,
        study_item_id=item.id,
        result=grade,
        old_times_review=old["times_review"],
        new_times_review=item.times_review,
        old_passed=old["passed"],
        new_passed=item.passed,
        old_wrong_count=old["wrong_count"],
        new_wrong_count=item.wrong_count,
        old_hard_level=old["hard_level"],
        new_hard_level=item.hard_level,
        old_next_review_date=old["next_review_date"],
        new_next_review_date=item.next_review_date,
        old_ease=old["ease"],
        new_ease=item.ease,
        old_interval_days=old["interval_days"],
        new_interval_days=item.interval_days,
        old_last_result=old["last_result"],
        old_last_date_review=old["last_date_review"],
        self_note=self_note,
        study_date=today,
    ))

    # Single transaction (spec 12.3) — any failure above rolls everything back.
    await db.commit()
    await db.refresh(session)
    await db.refresh(item)
    return _build_response(session, session_item, item, already_applied=False)


async def undo_review(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    session_item_id: uuid.UUID,
) -> UndoResponse:
    """Single-step undo of the MOST RECENT answered card in an active session."""
    session = await get_session(db, user_id, session_id)
    if session.status != "ACTIVE":
        raise ConflictError(f"Session is {session.status}")

    session_item = await db.scalar(
        select(StudySessionItem).where(
            StudySessionItem.id == session_item_id,
            StudySessionItem.session_id == session.id,
        )
    )
    if session_item is None:
        raise NotFoundError("Session item")
    if session_item.applied_at is None:
        raise ConflictError("This card has not been answered yet")

    latest = await db.scalar(
        select(StudySessionItem)
        .where(
            StudySessionItem.session_id == session.id,
            StudySessionItem.applied_at.is_not(None),
        )
        .order_by(StudySessionItem.applied_at.desc())
        .limit(1)
    )
    if latest is None or latest.id != session_item.id:
        raise ConflictError("Only the most recently answered card can be undone")

    item = await db.scalar(
        select(StudyItem).where(
            StudyItem.id == session_item.study_item_id, StudyItem.user_id == user_id
        )
    )
    if item is None:
        raise NotFoundError("Study item")

    log = await db.scalar(
        select(ReviewLog)
        .where(
            ReviewLog.session_id == session.id,
            ReviewLog.study_item_id == item.id,
        )
        .order_by(ReviewLog.created_at.desc())
        .limit(1)
    )
    if log is None:
        raise ConflictError("No review log found for this card")

    grade = session_item.result

    # Restore item from the snapshot
    item.times_review = log.old_times_review or 0
    item.passed = bool(log.old_passed)
    item.wrong_count = log.old_wrong_count or 0
    item.hard_level = log.old_hard_level or "Normal"
    item.next_review_date = log.old_next_review_date
    if log.old_ease is not None:
        item.ease = log.old_ease
    item.interval_days = log.old_interval_days or 0
    item.last_result = log.old_last_result
    item.last_date_review = log.old_last_date_review

    # Roll back session counters
    session.completed_items = max(0, session.completed_items - 1)
    if grade in REMEMBER_GRADES:
        session.pass_count = max(0, session.pass_count - 1)
    elif grade == "AGAIN":
        session.fail_count = max(0, session.fail_count - 1)
    else:
        session.skip_count = max(0, session.skip_count - 1)

    session_item.result = None
    session_item.applied_at = None
    await db.delete(log)

    await db.commit()
    await db.refresh(session)
    await db.refresh(item)
    return UndoResponse(
        session_item_id=session_item.id,
        study_item_id=item.id,
        undone_result=grade,
        restored=_progress_of(item),
        session_progress=_session_progress_of(session),
    )


def _progress_of(item) -> NewProgress:
    return NewProgress(
        times_review=item.times_review,
        passed=item.passed,
        wrong_count=item.wrong_count,
        hard_level=item.hard_level,
        next_review_date=item.next_review_date,
        ease=item.ease,
        interval_days=item.interval_days,
    )


def _session_progress_of(session) -> SessionProgress:
    return SessionProgress(
        completed_items=session.completed_items,
        total_items=session.total_items,
        pass_count=session.pass_count,
        fail_count=session.fail_count,
        skip_count=session.skip_count,
    )


def _build_response(session, session_item, item, *, already_applied: bool) -> ReviewResponse:
    return ReviewResponse(
        session_item_id=session_item.id,
        study_item_id=item.id,
        result=session_item.result,
        already_applied=already_applied,
        new_progress=_progress_of(item),
        session_progress=_session_progress_of(session),
    )
