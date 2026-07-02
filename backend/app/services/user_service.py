import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserSetting


async def get_or_create_user_settings(db: AsyncSession, user_id: uuid.UUID) -> UserSetting:
    settings = await db.scalar(select(UserSetting).where(UserSetting.user_id == user_id))
    if settings is None:
        settings = UserSetting(user_id=user_id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


async def get_user_timezone(db: AsyncSession, user_id: uuid.UUID) -> str:
    settings = await get_or_create_user_settings(db, user_id)
    return settings.timezone
