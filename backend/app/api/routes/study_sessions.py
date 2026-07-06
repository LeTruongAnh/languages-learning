"""Study sessions + review submission (spec 10.5)."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.study_item import merged_out
from app.schemas.study_session import (
    ReviewRequest,
    ReviewResponse,
    SessionItemOut,
    SessionOut,
    UndoResponse,
)
from app.services import review_service, study_session_service

router = APIRouter(tags=["study-sessions"])


async def _session_out(db, session, stats: dict | None = None) -> SessionOut:
    triples = await study_session_service.load_session_items(db, session)
    return SessionOut(
        **(stats or {}),
        id=session.id,
        language_id=session.language_id,
        session_type=session.session_type,
        status=session.status,
        study_date=session.study_date,
        total_items=session.total_items,
        completed_items=session.completed_items,
        pass_count=session.pass_count,
        fail_count=session.fail_count,
        skip_count=session.skip_count,
        items=[
            SessionItemOut(
                id=si.id,
                position=si.position,
                planned_bucket=si.planned_bucket,
                result=si.result,
                item=merged_out(item, prog),
            )
            for si, item, prog in triples
        ],
    )


@router.post(
    "/languages/{language_id}/study-sessions/daily",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_daily(
    language_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await study_session_service.get_or_create_daily(db, current_user.id, language_id)
    return await _session_out(db, session)


@router.post(
    "/languages/{language_id}/study-sessions/extra",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_extra(
    language_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await study_session_service.create_extra(db, current_user.id, language_id)
    return await _session_out(db, session)


@router.post(
    "/languages/{language_id}/study-sessions/weekly",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_weekly(
    language_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Weekly review: re-drill last 7 days' items, hardest first."""
    session = await study_session_service.create_weekly(db, current_user.id, language_id)
    return await _session_out(db, session)


@router.get("/languages/{language_id}/study-sessions/current", response_model=SessionOut)
async def get_current(
    language_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await study_session_service.get_current(db, current_user.id, language_id)
    return await _session_out(db, session)


@router.get("/study-sessions/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await study_session_service.get_session(db, current_user.id, session_id)
    return await _session_out(db, session)


@router.post(
    "/study-sessions/{session_id}/items/{session_item_id}/review",
    response_model=ReviewResponse,
)
async def submit_review(
    session_id: uuid.UUID,
    session_item_id: uuid.UUID,
    body: ReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await review_service.submit_review(
        db, current_user.id, session_id, session_item_id, body.result, body.self_note
    )


@router.post("/study-sessions/{session_id}/complete", response_model=SessionOut)
async def complete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await study_session_service.complete_session(db, current_user.id, session_id)
    stats = await study_session_service.completion_stats(db, current_user.id, session)
    return await _session_out(db, session, stats)


@router.post(
    "/study-sessions/{session_id}/items/{session_item_id}/undo",
    response_model=UndoResponse,
)
async def undo_review(
    session_id: uuid.UUID,
    session_item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Anki-style single-step undo: only the most recently answered card."""
    return await review_service.undo_review(
        db, current_user.id, session_id, session_item_id
    )
