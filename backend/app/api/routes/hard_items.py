"""Hard items (spec §10.6)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.routes.study_sessions import _session_out
from app.core.database import get_db
from app.models import User
from app.schemas.study_item import StudyItemOut, merged_out
from app.schemas.study_session import SessionOut
from app.services import study_session_service

router = APIRouter(prefix="/hard-items", tags=["hard-items"])


@router.get("", response_model=list[StudyItemOut])
async def list_hard_items(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    pairs = await study_session_service.list_hard_items(db, current_user.id)
    return [merged_out(item, prog) for item, prog in pairs]


@router.post("/study-sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_hard_session(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    session = await study_session_service.create_hard_items_session(db, current_user.id)
    return await _session_out(db, session)
