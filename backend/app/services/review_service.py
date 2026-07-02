"""Review submission (spec §8, §12.3, §12.4).

One transaction: study_item + session_item + review_log + session counters.
Idempotent: if session_item.applied_at is already set, return current state
without re-applying.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.timeutil import today_in_tz
from app.models import ReviewLog, StudyItem, StudySessionItem
from app.schemas.study_session import (
    NewProgress,
    ReviewResponse,
    SessionProgress,
)
from app.services.language_service import get_settings
from app.services.study_session_service import get_session
from app.services.user_service import get_user_timezone


def compute_hard_level(wrong_count: int) -> str:
    """Spec §8.2."""
    if wrong_count >= 3:
        return "Very Hard"
    if wrong_count >= 2:
        return "Hard"
    return "Normal"


def next_interval_days(intervals: list[int], times_review: int) -> int:
    """intervals[times_review], clamped to the last entry (PLAN.md §1.2#4).
    times_review is the value AFTER the pass increment (1-based)."""
    if not intervals:
        return 1
    index = min(times_review, len(intervals)) - 1
    return intervals[max(index, 0)]


async def submit_review(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    session_item_id: uuid.UUID,
    result: str,
    self_note: str | None = None,
) -> ReviewResponse:
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

    # Idempotency (spec §12.4): already applied -> return stored state.
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
    )

    if item.item_type == "SENTENCE":
        times_limit = settings.sentence_times_limit
        intervals = settings.sentence_review_intervals
    else:
        times_limit = settings.times_limit
        intervals = settings.review_intervals

    if result == "PASS":
        item.times_review = item.times_review + 1
        item.passed = item.times_review >= times_limit
        item.hard_level = compute_hard_level(item.wrong_count)
        item.next_review_date = (
            None if item.passed
            else today + timedelta(days=next_interval_days(intervals, item.times_review))
        )
        item.last_result = "PASS"
        item.last_date_review = today
    elif result == "FAIL":
        item.times_review = 0 if settings.reset_on_fail else item.times_review
        item.passed = False
        item.wrong_count = item.wrong_count + 1
        item.hard_level = compute_hard_level(item.wrong_count)
        item.next_review_date = today + timedelta(days=1)
        item.last_result = "FAIL"
        item.last_date_review = today
    # SKIP: no progress changes (spec §8.1)

    session_item.result = result
    session_item.applied_at = datetime.now(timezone.utc)

    session.completed_items += 1
    if result == "PASS":
        session.pass_count += 1
    elif result == "FAIL":
        session.fail_count += 1
    else:
        session.skip_count += 1

    db.add(ReviewLog(
        user_id=user_id,
        language_id=item.language_id,
        session_id=session.id,
        study_item_id=item.id,
        result=result,
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
        self_note=self_note,
        study_date=today,
    ))

    # Single transaction (spec §12.3) — any failure above rolls everything back.
    await db.commit()
    await db.refresh(session)
    await db.refresh(item)
    return _build_response(session, session_item, item, already_applied=False)


def _build_response(session, session_item, item, *, already_applied: bool) -> ReviewResponse:
    return ReviewResponse(
        session_item_id=session_item.id,
        study_item_id=item.id,
        result=session_item.result,
        already_applied=already_applied,
        new_progress=NewProgress(
            times_review=item.times_review,
            passed=item.passed,
            wrong_count=item.wrong_count,
            hard_level=item.hard_level,
            next_review_date=item.next_review_date,
        ),
        session_progress=SessionProgress(
            completed_items=session.completed_items,
            total_items=session.total_items,
            pass_count=session.pass_count,
            fail_count=session.fail_count,
            skip_count=session.skip_count,
        ),
    )
