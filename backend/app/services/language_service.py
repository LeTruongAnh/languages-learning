"""Languages are a GLOBAL catalog (admin-managed). Per-user state lives in
language_settings — created lazily on first access (auto-enroll).

NOTE: user_id params are kept in read functions for call-site compatibility;
reads are global."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models import Language, LanguageSetting
from app.schemas.language import LanguageCreate, LanguageSettingUpdate, LanguageUpdate


async def list_languages(db: AsyncSession, user_id: uuid.UUID | None = None) -> list[Language]:
    result = await db.scalars(
        select(Language)
        .where(Language.is_active.is_(True))
        .order_by(Language.sort_order, Language.created_at)
    )
    return list(result)


async def get_language(
    db: AsyncSession, user_id: uuid.UUID | None, language_id: uuid.UUID
) -> Language:
    lang = await db.scalar(select(Language).where(Language.id == language_id))
    if lang is None:
        raise NotFoundError("Language")
    return lang


async def create_language(db: AsyncSession, user_id: uuid.UUID, data: LanguageCreate) -> Language:
    dup = await db.scalar(select(Language).where(Language.code == data.code))
    if dup is not None:
        if not dup.is_active:  # reactivate soft-disabled language
            dup.is_active = True
            await db.commit()
            await db.refresh(dup)
            return dup
        raise ConflictError(f"Language '{data.code}' already exists")

    lang = Language(**data.model_dump())
    db.add(lang)
    await db.commit()
    await db.refresh(lang)
    return lang


async def update_language(
    db: AsyncSession, user_id: uuid.UUID, language_id: uuid.UUID, data: LanguageUpdate
) -> Language:
    lang = await get_language(db, user_id, language_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(lang, key, value)
    await db.commit()
    await db.refresh(lang)
    return lang


async def soft_delete_language(
    db: AsyncSession, user_id: uuid.UUID, language_id: uuid.UUID
) -> None:
    lang = await get_language(db, user_id, language_id)
    lang.is_active = False  # soft-disable per spec §10.2
    await db.commit()


async def get_settings(
    db: AsyncSession, user_id: uuid.UUID, language_id: uuid.UUID
) -> LanguageSetting:
    await get_language(db, user_id, language_id)  # 404 if unknown language
    settings = await db.scalar(
        select(LanguageSetting).where(
            LanguageSetting.user_id == user_id, LanguageSetting.language_id == language_id
        )
    )
    if settings is None:
        # Self-heal creates DEFAULTS but must NOT enroll: merely READING
        # settings (e.g. the Settings tab probing a language) used to
        # silently add the language to Home. Enrollment is explicit —
        # only sync_enrollments() sets is_active=True.
        settings = LanguageSetting(
            user_id=user_id, language_id=language_id, is_active=False
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


async def update_settings(
    db: AsyncSession, user_id: uuid.UUID, language_id: uuid.UUID, data: LanguageSettingUpdate
) -> LanguageSetting:
    settings = await get_settings(db, user_id, language_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    await db.commit()
    await db.refresh(settings)
    return settings


async def enrolled_language_ids(db: AsyncSession, user_id: uuid.UUID) -> set[uuid.UUID]:
    rows = await db.scalars(
        select(LanguageSetting.language_id).where(
            LanguageSetting.user_id == user_id, LanguageSetting.is_active.is_(True)
        )
    )
    return set(rows)


async def sync_enrollments(
    db: AsyncSession, user_id: uuid.UUID, language_ids: list[uuid.UUID]
) -> list[Language]:
    """Make the user's ACTIVE enrollments exactly `language_ids`.
    Un-enrolling only flips is_active=False — PROGRESS IS KEPT; re-enrolling
    restores the old settings untouched."""
    wanted = set(language_ids)
    catalog = {l.id: l for l in await list_languages(db)}
    for lid in wanted:
        if lid not in catalog:
            raise NotFoundError("Language")

    existing = {
        s.language_id: s
        for s in await db.scalars(
            select(LanguageSetting).where(LanguageSetting.user_id == user_id)
        )
    }
    for lid in wanted:
        if lid in existing:
            existing[lid].is_active = True
        else:
            db.add(LanguageSetting(user_id=user_id, language_id=lid))
    for lid, setting in existing.items():
        if lid not in wanted:
            setting.is_active = False
    await db.commit()
    return [catalog[lid] for lid in wanted]
