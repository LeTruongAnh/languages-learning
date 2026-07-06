"""Languages + language settings (spec 10.2, 10.3). All user-scoped."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.language import (
    EnrollmentUpdate,
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
    langs = await language_service.list_languages(db, current_user.id)
    enrolled = await language_service.enrolled_language_ids(db, current_user.id)
    out = []
    for lang in langs:
        o = LanguageOut.model_validate(lang)
        o.enrolled = lang.id in enrolled
        out.append(o)
    return out


@router.put("/enrollments", response_model=list[LanguageOut])
async def set_enrollments(
    body: EnrollmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync the user's studied-language set. Un-enroll keeps progress."""
    langs = await language_service.sync_enrollments(
        db, current_user.id, body.language_ids
    )
    out = []
    for lang in langs:
        o = LanguageOut.model_validate(lang)
        o.enrolled = True
        out.append(o)
    return out


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
