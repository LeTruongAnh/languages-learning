"""Catalog items: read for everyone (merged with own progress),
WRITE = ADMIN ONLY (shared content)."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.core.database import get_db
from app.core.timeutil import today_in_tz
from app.models import User
from app.schemas.study_item import (
    StudyItemCreate,
    StudyItemOut,
    StudyItemPage,
    StudyItemUpdate,
    merged_out,
)
from app.services import study_item_service
from app.services.user_service import get_user_timezone

router = APIRouter(prefix="/study-items", tags=["study-items"])


@router.get("", response_model=StudyItemPage)
async def list_items(
    language_id: uuid.UUID | None = Query(default=None, alias="languageId"),
    item_type: str | None = Query(default=None, alias="itemType"),
    difficulty: str | None = None,
    topic: str | None = None,
    situation: str | None = None,
    hard_level: str | None = Query(default=None, alias="hardLevel"),
    passed: bool | None = None,
    due_only: bool = Query(default=False, alias="dueOnly"),
    search: str | None = None,
    include_archived: bool = Query(default=False, alias="includeArchived"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200, alias="pageSize"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    due_date = None
    if due_only:
        due_date = today_in_tz(await get_user_timezone(db, current_user.id))
    pairs, total = await study_item_service.list_items(
        db,
        current_user.id,
        language_id=language_id,
        item_type=item_type,
        difficulty=difficulty,
        topic=topic,
        situation=situation,
        hard_level=hard_level,
        passed=passed,
        due_only=due_only,
        due_date=due_date,
        search=search,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )
    return StudyItemPage(
        items=[merged_out(item, prog) for item, prog in pairs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=StudyItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: StudyItemCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await study_item_service.create_item(db, body)
    return merged_out(item, None)


@router.get("/{item_id}", response_model=StudyItemOut)
async def get_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item, prog = await study_item_service.get_item_with_progress(
        db, current_user.id, item_id
    )
    return merged_out(item, prog)


@router.patch("/{item_id}", response_model=StudyItemOut)
async def update_item(
    item_id: uuid.UUID,
    body: StudyItemUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    item = await study_item_service.update_item(db, item_id, body)
    return merged_out(item, None)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Archive (soft delete) — hides the card from EVERY user's sessions."""
    await study_item_service.archive_item(db, item_id)
