"""User-level settings (timezone, TTS defaults — spec §7.8)."""

from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.common import CamelModel
from app.services.user_service import get_or_create_user_settings

router = APIRouter(prefix="/user-settings", tags=["user-settings"])


class UserSettingsOut(CamelModel):
    timezone: str
    auto_speak_on_card_open: bool
    speak_example: bool
    speech_rate: Decimal
    speech_volume: Decimal
    theme: str
    reminder_enabled: bool
    reminder_hour: int


class UserSettingsUpdate(CamelModel):
    timezone: str | None = Field(default=None, max_length=80)
    auto_speak_on_card_open: bool | None = None
    speak_example: bool | None = None
    speech_rate: Decimal | None = Field(default=None, ge=Decimal("0.1"), le=Decimal("2.0"))
    speech_volume: Decimal | None = Field(default=None, ge=Decimal("0.0"), le=Decimal("1.0"))
    theme: str | None = Field(default=None, pattern="^(system|light|dark)$")
    reminder_enabled: bool | None = None
    reminder_hour: int | None = Field(default=None, ge=0, le=23)


@router.get("", response_model=UserSettingsOut)
async def get_settings(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await get_or_create_user_settings(db, current_user.id)


@router.patch("", response_model=UserSettingsOut)
async def update_settings(
    body: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await get_or_create_user_settings(db, current_user.id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    await db.commit()
    await db.refresh(settings)
    return settings
