"""Study session engine (spec §9): candidate selection, ratio split,
bucket ordering, daily/extra/hard-items sessions."""

import uuid
from datetime import date

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.timeutil import today_in_tz
from app.models import Language, LanguageSetting, StudyItem, StudySession, StudySessionItem
from app.services.language_service import get_language, get_settings
from app.services.user_service import get_user_timezone

VOCAB = "VOCABULARY"
SENTENCE = "SENTENCE"


def _apply_list_filter(query, column, values: list[str]):
    if values and "ALL" not in values:
        query = query.where(column.in_(values))
    return query


def _base_candidates(user_id, language_id, item_type, settings: LanguageSetting):
    q = select(StudyItem).where(
        StudyItem.user_id == user_id,
        StudyItem.language_id == language_id,
        StudyItem.item_type == item_type,
        StudyItem.is_archived.is_(False),
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
        q = q.where(
            StudyItem.times_review == 0,
            StudyItem.passed.is_(False),
            StudyItem.last_date_review.is_(None),
        )
    else:  # REVIEW (spec §9.3) + optional re-review of passed items
        due_not_passed = (StudyItem.passed.is_(False)) & (StudyItem.next_review_date <= today)
        if settings.include_passed_items:
            from datetime import timedelta

            cutoff = today - timedelta(days=settings.passed_review_after_days)
            q = q.where(or_(
                due_not_passed,
                (StudyItem.passed.is_(True)) & (StudyItem.last_date_review <= cutoff),
            ))
        else:
            q = q.where(due_not_passed)

    if settings.avoid_same_day_repeat:
        q = q.where(or_(
            StudyItem.last_date_review.is_(None), StudyItem.last_date_review != today
        ))
    if exclude_ids:
        q = q.where(StudyItem.id.not_in(exclude_ids))

    if settings.sort_mode == "random":
        q = q.order_by(func.random())
    else:
        q = q.order_by(StudyItem.created_at)
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
    """VOCAB_FIRST_WITH_REVIEW_PRIORITY (spec §9.5). Other orderings can be
    added later; default is used for all sort modes in MVP."""
    arranged: list[tuple[StudyItem, str]] = []
    arranged += [(i, "VOCAB_REVIEW") for i in vocab_review]
    arranged += [(i, "VOCAB_NEW") for i in vocab_new]
    arranged += [(i, "SENTENCE_REVIEW") for i in sent_review]
    arranged += [(i, "SENTENCE_NEW") for i in sent_new]
    return arranged


async def _expire_stale_sessions(db: AsyncSession, user_id: uuid.UUID, today: date) -> None:
    """Sessions left ACTIVE from previous days become EXPIRED (PLAN.md §1.2#6)."""
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
    await get_language(db, user_id, language_id)  # 404 if not owned
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
    db: AsyncSession, session_id: uuid.UUID
) -> list[tuple[StudySessionItem, StudyItem]]:
    rows = await db.execute(
        select(StudySessionItem, StudyItem)
        .join(StudyItem, StudySessionItem.study_item_id == StudyItem.id)
        .where(StudySessionItem.session_id == session_id)
        .order_by(StudySessionItem.position)
    )
    return [(si, item) for si, item in rows.all()]


async def complete_session(db, user_id, session_id) -> StudySession:
    from datetime import datetime, timezone

    session = await get_session(db, user_id, session_id)
    if session.status == "ACTIVE":
        session.status = "COMPLETED"
        session.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(session)
    return session


HARD_LEVELS = ("Hard", "Very Hard")
HARD_SESSION_CAP = 50


async def create_hard_items_session(db: AsyncSession, user_id: uuid.UUID) -> StudySession:
    today = today_in_tz(await get_user_timezone(db, user_id))
    await _expire_stale_sessions(db, user_id, today)

    rows = await db.scalars(
        select(StudyItem)
        .where(
            StudyItem.user_id == user_id,
            StudyItem.is_archived.is_(False),
            StudyItem.passed.is_(False),
            StudyItem.hard_level.in_(HARD_LEVELS),
        )
        .order_by(StudyItem.wrong_count.desc())
        .limit(HARD_SESSION_CAP)
    )
    items = list(rows)
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


async def list_hard_items(db: AsyncSession, user_id: uuid.UUID) -> list[StudyItem]:
    rows = await db.scalars(
        select(StudyItem)
        .where(
            StudyItem.user_id == user_id,
            StudyItem.is_archived.is_(False),
            StudyItem.hard_level.in_(HARD_LEVELS),
        )
        .order_by(StudyItem.wrong_count.desc())
    )
    return list(rows)
