"""Languages + language settings (spec 10.2, 10.3). All user-scoped."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.language import (
    LanguageCreate,
    LanguageOut,
    LanguageSettingOut,
    LanguageSettingUpdate,
    LanguageUpdate,
)
from app.services import language_service, study_session_service

router = APIRouter(prefix="/languages", tags=["languages"])


@router.get("", response_model=list[LanguageOut])
async def list_languages(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await language_service.list_languages(db, current_user.id)


@router.post("", response_model=LanguageOut, status_code=status.HTTP_201_CREATED)
async def create_language(
    body: LanguageCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await language_service.create_language(db, current_user.id, body)


@router.get("/{language_id}", response_model=LanguageOut)
async def get_language(
    language_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await language_service.get_language(db, current_user.id, language_id)


@router.patch("/{language_id}", response_model=LanguageOut)
async def update_language(
    language_id: uuid.UUID,
    body: LanguageUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    return await language_service.update_language(db, current_user.id, language_id, body)


@router.delete("/{language_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_language(
    language_id: uuid.UUID,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    await language_service.soft_delete_language(db, current_user.id, language_id)


@router.get("/{language_id}/settings", response_model=LanguageSettingOut)
async def get_settings(
    language_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await language_service.get_settings(db, current_user.id, language_id)


@router.patch("/{language_id}/settings", response_model=LanguageSettingOut)
async def update_settings(
    language_id: uuid.UUID,
    body: LanguageSettingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await language_service.update_settings(db, current_user.id, language_id, body)


@router.get("/{language_id}/facets")
async def get_facets(
    language_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Distinct difficulty/topic/frequency/situation values for filter UI."""
    return await study_session_service.get_facets(db, current_user.id, language_id)
