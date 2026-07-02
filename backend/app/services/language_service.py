import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models import Language, LanguageSetting
from app.schemas.language import LanguageCreate, LanguageSettingUpdate, LanguageUpdate


async def list_languages(db: AsyncSession, user_id: uuid.UUID) -> list[Language]:
    result = await db.scalars(
        select(Language)
        .where(Language.user_id == user_id, Language.is_active.is_(True))
        .order_by(Language.sort_order, Language.created_at)
    )
    return list(result)


async def get_language(db: AsyncSession, user_id: uuid.UUID, language_id: uuid.UUID) -> Language:
    lang = await db.scalar(
        select(Language).where(Language.id == language_id, Language.user_id == user_id)
    )
    if lang is None:
        raise NotFoundError("Language")
    return lang


async def create_language(db: AsyncSession, user_id: uuid.UUID, data: LanguageCreate) -> Language:
    dup = await db.scalar(
        select(Language).where(Language.user_id == user_id, Language.code == data.code)
    )
    if dup is not None:
        if not dup.is_active:  # reactivate soft-disabled language
            dup.is_active = True
            await db.commit()
            await db.refresh(dup)
            return dup
        raise ConflictError(f"Language '{data.code}' already exists")

    lang = Language(user_id=user_id, **data.model_dump())
    db.add(lang)
    await db.flush()
    db.add(LanguageSetting(user_id=user_id, language_id=lang.id))  # defaults
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
    await get_language(db, user_id, language_id)  # ownership check -> 404
    settings = await db.scalar(
        select(LanguageSetting).where(
            LanguageSetting.user_id == user_id, LanguageSetting.language_id == language_id
        )
    )
    if settings is None:  # self-heal: create defaults
        settings = LanguageSetting(user_id=user_id, language_id=language_id)
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
