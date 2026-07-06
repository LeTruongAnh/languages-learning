"""Audio pronunciation endpoint.

Errors during generation are logged to the server console for debugging.

GET /tts/{item_id} -> mp3 (generated on first request, cached forever).
Auth: Bearer header OR ?token= (HTML audio elements can't send headers).
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_or_query_token
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models import Language, StudyItem, User
from app.services import tts_service

logger = logging.getLogger("vocab.tts")

router = APIRouter(prefix="/tts", tags=["tts"])


@router.get("/{item_id}")
async def get_audio(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user_or_query_token),
    db: AsyncSession = Depends(get_db),
):
    row = (await db.execute(
        select(StudyItem.text, Language.tts_lang)
        .join(Language, StudyItem.language_id == Language.id)
        .where(StudyItem.id == item_id)
    )).first()
    if row is None:
        raise NotFoundError("Study item")

    try:
        path = await tts_service.get_or_generate(item_id, row.text, row.tts_lang)
    except ModuleNotFoundError as exc:
        logger.error("edge-tts chua duoc cai: pip install -e \".[dev]\"")
        raise HTTPException(
            status_code=503,
            detail="edge-tts is not installed on the server (pip install -e '.[dev]')",
        ) from exc
    except Exception as exc:  # network down / edge endpoint changed
        logger.exception("TTS generation failed for item %s", item_id)
        raise HTTPException(status_code=503, detail=f"TTS generation failed: {exc}") from exc

    return FileResponse(
        path,
        media_type="audio/mpeg",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )
