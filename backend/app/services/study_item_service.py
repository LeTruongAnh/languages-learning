import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import StudyItem
from app.schemas.study_item import StudyItemCreate, StudyItemUpdate
from app.services.language_service import get_language


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
) -> tuple[list[StudyItem], int]:
    query = select(StudyItem).where(StudyItem.user_id == user_id)
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
        query = query.where(StudyItem.hard_level == hard_level)
    if passed is not None:
        query = query.where(StudyItem.passed.is_(passed))
    if due_only and due_date is not None:
        query = query.where(
            StudyItem.passed.is_(False), StudyItem.next_review_date <= due_date
        )
    if search:
        like = f"%{search}%"
        query = query.where(
            or_(StudyItem.text.ilike(like), StudyItem.vietnamese_meaning.ilike(like))
        )

    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = await db.scalars(
        query.order_by(StudyItem.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total


async def get_item(db: AsyncSession, user_id: uuid.UUID, item_id: uuid.UUID) -> StudyItem:
    item = await db.scalar(
        select(StudyItem).where(StudyItem.id == item_id, StudyItem.user_id == user_id)
    )
    if item is None:
        raise NotFoundError("Study item")
    return item


async def create_item(db: AsyncSession, user_id: uuid.UUID, data: StudyItemCreate) -> StudyItem:
    await get_language(db, user_id, data.language_id)  # ownership check -> 404
    item = StudyItem(user_id=user_id, **data.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_item(
    db: AsyncSession, user_id: uuid.UUID, item_id: uuid.UUID, data: StudyItemUpdate
) -> StudyItem:
    item = await get_item(db, user_id, item_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


async def archive_item(db: AsyncSession, user_id: uuid.UUID, item_id: uuid.UUID) -> None:
    item = await get_item(db, user_id, item_id)
    item.is_archived = True
    await db.commit()
