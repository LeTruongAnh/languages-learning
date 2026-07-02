"""Dashboard (spec 10.7)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.dashboard import HistoryDay, LanguageSummary, TodaySummary
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=TodaySummary)
async def summary(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await dashboard_service.summary(db, current_user.id)


@router.get("/languages", response_model=list[LanguageSummary])
async def languages(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await dashboard_service.languages(db, current_user.id)


@router.get("/history", response_model=list[HistoryDay])
async def history(
    range_: str = Query(default="30d", alias="range", pattern=r"^\d{1,3}d$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    days = min(int(range_.rstrip("d")), 365)
    return await dashboard_service.history(db, current_user.id, days)
