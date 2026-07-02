"""Dashboard aggregations (spec §10.7). 'Today' always in the user's timezone."""

import uuid
from datetime import date, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timeutil import today_in_tz
from app.models import Language, LanguageSetting, ReviewLog, StudyItem
from app.schemas.dashboard import HistoryDay, LanguageSummary, TodaySummary
from app.services.study_session_service import HARD_LEVELS

# Grade categories (SRS v2): remembered vs forgotten, legacy aliases included.
REMEMBERED = ("PASS", "HARD", "GOOD", "EASY")
FORGOTTEN = ("FAIL", "AGAIN")
from app.services.user_service import get_user_timezone


def _result_counts_query(user_id: uuid.UUID):
    return select(
        func.count().label("learned"),
        func.sum(case((ReviewLog.result.in_(REMEMBERED), 1), else_=0)).label("pass_count"),
        func.sum(case((ReviewLog.result.in_(FORGOTTEN), 1), else_=0)).label("fail_count"),
        func.sum(case((ReviewLog.result == "SKIP", 1), else_=0)).label("skip_count"),
    ).where(ReviewLog.user_id == user_id)


async def summary(db: AsyncSession, user_id: uuid.UUID) -> TodaySummary:
    today = today_in_tz(await get_user_timezone(db, user_id))

    row = (await db.execute(
        _result_counts_query(user_id).where(ReviewLog.study_date == today)
    )).one()
    pass_count = row.pass_count or 0
    fail_count = row.fail_count or 0
    skip_count = row.skip_count or 0
    graded = pass_count + fail_count
    pass_rate = (pass_count / graded) if graded else 0.0

    due_today = await db.scalar(
        select(func.count()).select_from(StudyItem).where(
            StudyItem.user_id == user_id,
            StudyItem.is_archived.is_(False),
            StudyItem.passed.is_(False),
            StudyItem.next_review_date <= today,
        )
    ) or 0

    hard_count = await db.scalar(
        select(func.count()).select_from(StudyItem).where(
            StudyItem.user_id == user_id,
            StudyItem.is_archived.is_(False),
            StudyItem.hard_level.in_(HARD_LEVELS),
        )
    ) or 0

    streak = await _streak_days(db, user_id, today)

    return TodaySummary(
        today_learned=row.learned or 0,
        pass_count=pass_count,
        fail_count=fail_count,
        skip_count=skip_count,
        pass_rate=round(pass_rate, 4),
        streak_days=streak,
        due_today=due_today,
        hard_items_count=hard_count,
    )


async def _streak_days(db: AsyncSession, user_id: uuid.UUID, today: date) -> int:
    """Consecutive study days ending today/yesterday, with STREAK PROTECTION:
    one single-day gap is forgiven (Duolingo-style freeze, simplified)."""
    rows = await db.scalars(
        select(ReviewLog.study_date)
        .where(ReviewLog.user_id == user_id, ReviewLog.study_date.is_not(None))
        .group_by(ReviewLog.study_date)
        .order_by(ReviewLog.study_date.desc())
        .limit(400)
    )
    days = list(rows)
    if not days:
        return 0
    grace = 1  # forgivable one-day gaps
    one = timedelta(days=1)
    # Start today, yesterday, or the day before (consuming grace).
    if days[0] == today or days[0] == today - one:
        cursor = days[0]
    elif days[0] == today - 2 * one and grace:
        grace = 0
        cursor = days[0]
    else:
        return 0
    streak = 0
    for d in days:
        if d == cursor:
            streak += 1
            cursor -= one
        elif d == cursor - one and grace:
            grace = 0
            streak += 1
            cursor = d - one
        elif d < cursor:
            break
    return streak


async def languages(db: AsyncSession, user_id: uuid.UUID) -> list[LanguageSummary]:
    today = today_in_tz(await get_user_timezone(db, user_id))
    langs = list(await db.scalars(
        select(Language)
        .where(Language.user_id == user_id, Language.is_active.is_(True))
        .order_by(Language.sort_order, Language.created_at)
    ))

    summaries: list[LanguageSummary] = []
    for lang in langs:
        base = select(func.count()).select_from(StudyItem).where(
            StudyItem.user_id == user_id,
            StudyItem.language_id == lang.id,
            StudyItem.is_archived.is_(False),
        )
        due = await db.scalar(base.where(
            StudyItem.passed.is_(False), StudyItem.next_review_date <= today
        )) or 0
        new = await db.scalar(base.where(
            StudyItem.times_review == 0,
            StudyItem.passed.is_(False),
            StudyItem.last_date_review.is_(None),
        )) or 0
        vocab = await db.scalar(base.where(
            StudyItem.item_type == "VOCABULARY",
            StudyItem.passed.is_(False),
        )) or 0
        sentence = await db.scalar(base.where(
            StudyItem.item_type == "SENTENCE",
            StudyItem.passed.is_(False),
        )) or 0
        today_learned = await db.scalar(
            select(func.count()).select_from(ReviewLog).where(
                ReviewLog.user_id == user_id,
                ReviewLog.language_id == lang.id,
                ReviewLog.study_date == today,
            )
        ) or 0
        daily_limit = await db.scalar(
            select(LanguageSetting.daily_limit).where(
                LanguageSetting.user_id == user_id,
                LanguageSetting.language_id == lang.id,
            )
        ) or 20

        summaries.append(LanguageSummary(
            language_id=lang.id,
            code=lang.code,
            name=lang.name,
            accent_color=lang.accent_color,
            tts_lang=lang.tts_lang,
            due_count=due,
            new_count=new,
            vocab_due_new=vocab,
            sentence_due_new=sentence,
            today_learned=today_learned,
            daily_limit=daily_limit,
        ))
    return summaries


async def history(db: AsyncSession, user_id: uuid.UUID, days: int = 30) -> list[HistoryDay]:
    today = today_in_tz(await get_user_timezone(db, user_id))
    since = today - timedelta(days=days - 1)
    rows = (await db.execute(
        select(
            ReviewLog.study_date,
            func.count().label("learned"),
            func.sum(case((ReviewLog.result.in_(REMEMBERED), 1), else_=0)).label("pass_count"),
            func.sum(case((ReviewLog.result.in_(FORGOTTEN), 1), else_=0)).label("fail_count"),
            func.sum(case((ReviewLog.result == "SKIP", 1), else_=0)).label("skip_count"),
        )
        .where(
            ReviewLog.user_id == user_id,
            ReviewLog.study_date >= since,
            ReviewLog.study_date.is_not(None),
        )
        .group_by(ReviewLog.study_date)
        .order_by(ReviewLog.study_date)
    )).all()
    return [
        HistoryDay(
            day=r.study_date,
            learned=r.learned,
            pass_count=r.pass_count or 0,
            fail_count=r.fail_count or 0,
            skip_count=r.skip_count or 0,
        )
        for r in rows
    ]
