"""Study session engine (spec §9) on the CATALOG + PROGRESS split:
catalog items are shared; per-user SRS state is LEFT JOINed from
user_item_progress. Missing progress row == NEW card (lazy creation)."""

import uuid
from datetime import date

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.timeutil import today_in_tz
from app.models import (
    Language,
    LanguageSetting,
    StudyItem,
    StudySession,
    StudySessionItem,
    UserItemProgress,
)
from app.services.language_service import get_language, get_settings
from app.services.user_service import get_user_timezone

VOCAB = "VOCABULARY"
SENTENCE = "SENTENCE"

P = UserItemProgress  # alias for brevity in join-heavy queries


def _progress_on(user_id: uuid.UUID):
    return and_(P.item_id == StudyItem.id, P.user_id == user_id)


def _fresh_clause():
    """NEW card: never graded (no progress row, or zeroed by undo)."""
    return or_(
        P.id.is_(None),
        and_(P.times_review == 0, P.passed.is_(False), P.last_date_review.is_(None)),
    )


def _apply_list_filter(query, column, values: list[str]):
    if values and "ALL" not in values:
        query = query.where(column.in_(values))
    return query


def _base_candidates(user_id, language_id, item_type, settings: LanguageSetting):
    q = (
        select(StudyItem)
        .join(P, _progress_on(user_id), isouter=True)
        .where(
            StudyItem.language_id == language_id,
            StudyItem.item_type == item_type,
            StudyItem.is_archived.is_(False),
        )
    )
    difficulty = (
        settings.sentence_difficulty_filter if item_type == SENTENCE
        else settings.difficulty_filter
    )
    q = _apply_list_filter(q, StudyItem.difficulty, difficulty)
    q = _apply_list_filter(q, StudyItem.topic, settings.topic_filter)
    if item_type == SENTENCE:
        q = _apply_list_filter(q, StudyItem.situation, settings.situation_filter)
    q = _apply_list_filter(q, StudyItem.frequency_level, settings.frequency_filter)
    return q


async def _pick_bucket(
    db: AsyncSession,
    user_id: uuid.UUID,
    language_id: uuid.UUID,
    item_type: str,
    kind: str,  # 'NEW' | 'REVIEW'
    limit: int,
    settings: LanguageSetting,
    today: date,
    exclude_ids: set[uuid.UUID],
) -> list[StudyItem]:
    if limit <= 0:
        return []
    q = _base_candidates(user_id, language_id, item_type, settings)

    if kind == "NEW":
        q = q.where(_fresh_clause())
    else:  # REVIEW (spec §9.3) + optional re-review of passed items
        due_not_passed = (P.passed.is_(False)) & (P.next_review_date <= today)
        if settings.include_passed_items:
            from datetime import timedelta

            cutoff = today - timedelta(days=settings.passed_review_after_days)
            q = q.where(or_(
                due_not_passed,
                (P.passed.is_(True)) & (P.last_date_review <= cutoff),
            ))
        else:
            q = q.where(due_not_passed)

    if settings.avoid_same_day_repeat:
        q = q.where(or_(
            P.id.is_(None), P.last_date_review.is_(None), P.last_date_review != today
        ))
    if exclude_ids:
        q = q.where(StudyItem.id.not_in(exclude_ids))

    if settings.sort_mode == "priority":
        # Hardest first: most wrong answers, then most overdue.
        q = q.order_by(
            func.coalesce(P.wrong_count, 0).desc(), P.next_review_date.asc()
        )
    elif settings.sort_mode == "oldest_first":
        q = q.order_by(StudyItem.created_at)
    else:  # random (default)
        q = q.order_by(func.random())
    rows = await db.scalars(q.limit(limit))
    return list(rows)


async def _pick_items(
    db, user_id, language_id, item_type, limit, settings, today, exclude_ids
) -> tuple[list[StudyItem], list[StudyItem]]:
    """Returns (review_items, new_items) with ratio + fallback fill (spec §9.4)."""
    if limit <= 0:
        return [], []
    new_limit = round(limit * float(settings.new_ratio))
    review_limit = limit - new_limit

    review = await _pick_bucket(
        db, user_id, language_id, item_type, "REVIEW", review_limit, settings, today, exclude_ids
    )
    exclude = exclude_ids | {i.id for i in review}
    new = await _pick_bucket(
        db, user_id, language_id, item_type, "NEW", new_limit, settings, today, exclude
    )
    # Fallback fill: top up from the other bucket if one fell short.
    shortfall = limit - len(review) - len(new)
    if shortfall > 0:
        exclude = exclude | {i.id for i in new}
        extra_review = await _pick_bucket(
            db, user_id, language_id, item_type, "REVIEW", shortfall, settings, today, exclude
        )
        review += extra_review
        shortfall -= len(extra_review)
        if shortfall > 0:
            exclude = exclude | {i.id for i in extra_review}
            new += await _pick_bucket(
                db, user_id, language_id, item_type, "NEW", shortfall, settings, today, exclude
            )
    return review, new


def _arrange(vocab_review, vocab_new, sent_review, sent_new) -> list[tuple[StudyItem, str]]:
    """VOCAB_FIRST_WITH_REVIEW_PRIORITY (spec §9.5)."""
    arranged: list[tuple[StudyItem, str]] = []
    arranged += [(i, "VOCAB_REVIEW") for i in vocab_review]
    arranged += [(i, "VOCAB_NEW") for i in vocab_new]
    arranged += [(i, "SENTENCE_REVIEW") for i in sent_review]
    arranged += [(i, "SENTENCE_NEW") for i in sent_new]
    return arranged


async def _expire_stale_sessions(db: AsyncSession, user_id: uuid.UUID, today: date) -> None:
    await db.execute(
        update(StudySession)
        .where(
            StudySession.user_id == user_id,
            StudySession.status == "ACTIVE",
            StudySession.study_date < today,
        )
        .values(status="EXPIRED")
    )


async def _create_language_session(
    db: AsyncSession, user_id: uuid.UUID, language_id: uuid.UUID, session_type: str
) -> StudySession:
    settings = await get_settings(db, user_id, language_id)
    today = today_in_tz(await get_user_timezone(db, user_id))
    await _expire_stale_sessions(db, user_id, today)

    if session_type == "LANGUAGE_DAILY":
        existing = await db.scalar(
            select(StudySession).where(
                StudySession.user_id == user_id,
                StudySession.language_id == language_id,
                StudySession.session_type == "LANGUAGE_DAILY",
                StudySession.study_date == today,
                StudySession.status == "ACTIVE",
            )
        )
        if existing is not None:
            return existing

    vocab_limit = round(settings.daily_limit * float(settings.vocabulary_ratio))
    sentence_limit = settings.daily_limit - vocab_limit

    vocab_review, vocab_new = await _pick_items(
        db, user_id, language_id, VOCAB, vocab_limit, settings, today, set()
    )
    picked = {i.id for i in vocab_review + vocab_new}
    sent_review, sent_new = await _pick_items(
        db, user_id, language_id, SENTENCE, sentence_limit, settings, today, picked
    )
    arranged = _arrange(vocab_review, vocab_new, sent_review, sent_new)

    session = StudySession(
        user_id=user_id,
        language_id=language_id,
        session_type=session_type,
        study_date=today,
        total_items=len(arranged),
    )
    db.add(session)
    await db.flush()
    for position, (item, bucket) in enumerate(arranged, start=1):
        db.add(StudySessionItem(
            session_id=session.id,
            study_item_id=item.id,
            position=position,
            planned_bucket=bucket,
        ))
    await db.commit()
    await db.refresh(session)
    return session


async def get_or_create_daily(db, user_id, language_id) -> StudySession:
    await get_language(db, user_id, language_id)  # 404 if unknown
    return await _create_language_session(db, user_id, language_id, "LANGUAGE_DAILY")


async def create_extra(db, user_id, language_id) -> StudySession:
    await get_language(db, user_id, language_id)
    return await _create_language_session(db, user_id, language_id, "LANGUAGE_EXTRA")


async def get_current(db, user_id, language_id) -> StudySession:
    await get_language(db, user_id, language_id)
    today = today_in_tz(await get_user_timezone(db, user_id))
    session = await db.scalar(
        select(StudySession)
        .where(
            StudySession.user_id == user_id,
            StudySession.language_id == language_id,
            StudySession.study_date == today,
            StudySession.status == "ACTIVE",
        )
        .order_by(StudySession.created_at.desc())
    )
    if session is None:
        raise NotFoundError("Active session")
    return session


async def get_session(db, user_id, session_id) -> StudySession:
    session = await db.scalar(
        select(StudySession).where(
            StudySession.id == session_id, StudySession.user_id == user_id
        )
    )
    if session is None:
        raise NotFoundError("Session")
    return session


async def load_session_items(
    db: AsyncSession, session
) -> list[tuple[StudySessionItem, StudyItem, UserItemProgress | None]]:
    rows = await db.execute(
        select(StudySessionItem, StudyItem, P)
        .join(StudyItem, StudySessionItem.study_item_id == StudyItem.id)
        .join(P, _progress_on(session.user_id), isouter=True)
        .where(StudySessionItem.session_id == session.id)
        .order_by(StudySessionItem.position)
    )
    return [(si, item, prog) for si, item, prog in rows.all()]


async def complete_session(db, user_id, session_id) -> StudySession:
    from datetime import datetime, timezone

    session = await get_session(db, user_id, session_id)
    if session.status == "ACTIVE":
        session.status = "COMPLETED"
        session.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(session)
    return session


async def completion_stats(db, user_id, session) -> dict:
    """Emotional-completion payload: streak, record, cards graduated."""
    from app.services import dashboard_service

    today = today_in_tz(await get_user_timezone(db, user_id))
    streak = await dashboard_service.streak_days(db, user_id, today)
    longest = await dashboard_service.longest_streak_days(db, user_id)
    graduated = await db.scalar(
        select(func.count())
        .select_from(StudySessionItem)
        .join(P, and_(
            P.item_id == StudySessionItem.study_item_id, P.user_id == user_id
        ))
        .where(
            StudySessionItem.session_id == session.id,
            StudySessionItem.result.is_not(None),
            P.passed.is_(True),
        )
    ) or 0
    return {
        "streak_days": streak,
        "longest_streak": longest,
        "is_new_record": streak >= 2 and streak >= longest,
        "graduated_count": graduated,
    }


HARD_LEVELS = ("Hard", "Very Hard")
HARD_SESSION_CAP = 50


def _hard_query(user_id):
    return (
        select(StudyItem)
        .join(P, _progress_on(user_id))
        .where(
            StudyItem.is_archived.is_(False),
            P.passed.is_(False),
            P.hard_level.in_(HARD_LEVELS),
        )
        .order_by(P.wrong_count.desc())
    )


async def create_hard_items_session(db: AsyncSession, user_id: uuid.UUID) -> StudySession:
    today = today_in_tz(await get_user_timezone(db, user_id))
    await _expire_stale_sessions(db, user_id, today)

    items = list(await db.scalars(_hard_query(user_id).limit(HARD_SESSION_CAP)))
    if not items:
        raise NotFoundError("Hard items")

    session = StudySession(
        user_id=user_id,
        language_id=None,
        session_type="HARD_ITEMS",
        study_date=today,
        total_items=len(items),
    )
    db.add(session)
    await db.flush()
    for position, item in enumerate(items, start=1):
        bucket = "VOCAB_REVIEW" if item.item_type == VOCAB else "SENTENCE_REVIEW"
        db.add(StudySessionItem(
            session_id=session.id,
            study_item_id=item.id,
            position=position,
            planned_bucket=bucket,
        ))
    await db.commit()
    await db.refresh(session)
    return session


async def list_hard_items(db: AsyncSession, user_id: uuid.UUID):
    """Returns (item, progress) pairs — hardest first."""
    rows = await db.execute(
        select(StudyItem, P)
        .join(P, _progress_on(user_id))
        .where(
            StudyItem.is_archived.is_(False),
            P.passed.is_(False),
            P.hard_level.in_(HARD_LEVELS),
        )
        .order_by(P.wrong_count.desc())
    )
    return [(item, prog) for item, prog in rows.all()]


WEEKDAY_NAMES = [
    "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY",
]


async def create_weekly(db: AsyncSession, user_id: uuid.UUID, language_id: uuid.UUID) -> StudySession:
    """LANGUAGE_WEEKLY: re-drill items studied in the last 7 days."""
    from datetime import timedelta

    from app.models import ReviewLog

    await get_language(db, user_id, language_id)
    settings = await get_settings(db, user_id, language_id)
    today = today_in_tz(await get_user_timezone(db, user_id))
    await _expire_stale_sessions(db, user_id, today)

    existing = await db.scalar(
        select(StudySession).where(
            StudySession.user_id == user_id,
            StudySession.language_id == language_id,
            StudySession.session_type == "LANGUAGE_WEEKLY",
            StudySession.study_date == today,
            StudySession.status == "ACTIVE",
        )
    )
    if existing is not None:
        return existing

    since = today - timedelta(days=7)
    reviewed_ids = select(ReviewLog.study_item_id).where(
        ReviewLog.user_id == user_id,
        ReviewLog.language_id == language_id,
        ReviewLog.study_date >= since,
        ReviewLog.study_item_id.is_not(None),
    ).distinct()

    q = (
        select(StudyItem)
        .join(P, _progress_on(user_id), isouter=True)
        .where(
            StudyItem.language_id == language_id,
            StudyItem.is_archived.is_(False),
            StudyItem.id.in_(reviewed_ids),
        )
        .order_by(func.coalesce(P.wrong_count, 0).desc(), func.random())
        .limit(settings.weekly_review_limit)
    )
    if settings.avoid_same_day_repeat:
        q = q.where(or_(
            P.id.is_(None), P.last_date_review.is_(None), P.last_date_review != today
        ))
    items = list(await db.scalars(q))
    if not items:
        raise NotFoundError("Weekly review items")

    session = StudySession(
        user_id=user_id,
        language_id=language_id,
        session_type="LANGUAGE_WEEKLY",
        study_date=today,
        total_items=len(items),
    )
    db.add(session)
    await db.flush()
    for position, item in enumerate(items, start=1):
        bucket = "VOCAB_REVIEW" if item.item_type == VOCAB else "SENTENCE_REVIEW"
        db.add(StudySessionItem(
            session_id=session.id,
            study_item_id=item.id,
            position=position,
            planned_bucket=bucket,
        ))
    await db.commit()
    await db.refresh(session)
    return session


async def get_facets(db: AsyncSession, user_id: uuid.UUID, language_id: uuid.UUID) -> dict:
    """Distinct filter values from the CATALOG — powers the filter UI."""
    await get_language(db, user_id, language_id)

    async def distinct(column):
        rows = await db.scalars(
            select(column).where(
                StudyItem.language_id == language_id,
                StudyItem.is_archived.is_(False),
                column.is_not(None),
            ).distinct().order_by(column)
        )
        return [r for r in rows if r]

    return {
        "difficulties": await distinct(StudyItem.difficulty),
        "topics": await distinct(StudyItem.topic),
        "frequencyLevels": await distinct(StudyItem.frequency_level),
        "situations": await distinct(StudyItem.situation),
    }
