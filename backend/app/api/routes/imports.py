"""Import/export (spec 10.8)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.core.rate_limit import limiter
from app.models import ImportBatch, User
from app.schemas.common import CamelModel
from app.services import import_service
from app.services.import_service import MAX_FILE_BYTES

router = APIRouter(tags=["imports"])


class ImportBatchOut(CamelModel):
    id: uuid.UUID
    file_name: str | None
    status: str
    total_rows: int
    imported_rows: int
    failed_rows: int
    error_summary: str | None


@router.post(
    "/imports/study-items", response_model=ImportBatchOut, status_code=status.HTTP_201_CREATED
)
@limiter.limit("5/hour")
async def import_study_items(
    request: Request,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")
    return await import_service.import_csv(db, current_user.id, file.filename, content)


@router.get("/imports/{batch_id}", response_model=ImportBatchOut)
async def get_batch(
    batch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    batch = await db.scalar(
        select(ImportBatch).where(
            ImportBatch.id == batch_id, ImportBatch.user_id == current_user.id
        )
    )
    if batch is None:
        raise NotFoundError("Import batch")
    return batch


@router.get("/exports/study-items.csv")
async def export_csv(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    csv_text = await import_service.export_csv(db, current_user.id)
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=study-items.csv"},
    )


@router.get("/exports/backup.json")
async def export_backup(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    payload = await import_service.export_backup(db, current_user.id)
    return Response(
        payload,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=backup.json"},
    )
