"""Catalog CRUD (admin) + progress-merged reads (any user)."""

import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import StudyItem, UserItemProgress
from app.schemas.study_item import StudyItemCreate, StudyItemUpdate
from app.services.language_service import get_language

P = UserItemProgress


async def list_items(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    language_id: uuid.UUID | None = None,
    item_type: str | None = None,
    difficulty: str | None = None,
    topic: str | None = None,
    situation: str | None = None,
    hard_level: str | None = None,
    passed: bool | None = None,
    due_only: bool = False,
    due_date=None,
    search: str | None = None,
    include_archived: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[tuple[StudyItem, UserItemProgress | None]], int]:
    query = (
        select(StudyItem, P)
        .join(P, and_(P.item_id == StudyItem.id, P.user_id == user_id), isouter=True)
    )
    if not include_archived:
        query = query.where(StudyItem.is_archived.is_(False))
    if language_id is not None:
        query = query.where(StudyItem.language_id == language_id)
    if item_type:
        query = query.where(StudyItem.item_type == item_type)
    if difficulty:
        query = query.where(StudyItem.difficulty == difficulty)
    if topic:
        query = query.where(StudyItem.topic == topic)
    if situation:
        query = query.where(StudyItem.situation == situation)
    if hard_level:
        query = query.where(P.hard_level == hard_level)
    if passed is not None:
        if passed:
            query = query.where(P.passed.is_(True))
        else:
            query = query.where(or_(P.id.is_(None), P.passed.is_(False)))
    if due_only and due_date is not None:
        query = query.where(P.passed.is_(False), P.next_review_date <= due_date)
    if search:
        like = f"%{search}%"
        query = query.where(
            or_(StudyItem.text.ilike(like), StudyItem.vietnamese_meaning.ilike(like))
        )

    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = await db.execute(
        query.order_by(StudyItem.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [(item, prog) for item, prog in rows.all()], total


async def get_item(db: AsyncSession, item_id: uuid.UUID) -> StudyItem:
    item = await db.scalar(select(StudyItem).where(StudyItem.id == item_id))
    if item is None:
        raise NotFoundError("Study item")
    return item


async def get_item_with_progress(
    db: AsyncSession, user_id: uuid.UUID, item_id: uuid.UUID
) -> tuple[StudyItem, UserItemProgress | None]:
    item = await get_item(db, item_id)
    prog = await db.scalar(
        select(P).where(P.user_id == user_id, P.item_id == item_id)
    )
    return item, prog


async def create_item(db: AsyncSession, data: StudyItemCreate) -> StudyItem:
    await get_language(db, None, data.language_id)  # 404 if unknown
    item = StudyItem(**data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_item(
    db: AsyncSession, item_id: uuid.UUID, data: StudyItemUpdate
) -> StudyItem:
    item = await get_item(db, item_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


async def archive_item(db: AsyncSession, item_id: uuid.UUID) -> None:
    item = await get_item(db, item_id)
    item.is_archived = True
    await db.commit()
