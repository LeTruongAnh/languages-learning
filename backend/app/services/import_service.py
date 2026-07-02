"""CSV import/export (spec §10.8, §14).

CSV columns: language, item_type, text, pronunciation, vietnamese_meaning,
example, example_vietnamese, topic, situation, difficulty, frequency_level, notes.
'language' is the language code (zh, en, ...) and must already exist for the user.
"""

import csv
import io
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ImportBatch, Language, StudyItem

MAX_FILE_BYTES = 5 * 1024 * 1024  # PLAN.md §1.2#10
CSV_COLUMNS = [
    "language", "item_type", "text", "pronunciation", "vietnamese_meaning",
    "example", "example_vietnamese", "topic", "situation", "difficulty",
    "frequency_level", "notes",
]


async def import_csv(
    db: AsyncSession, user_id: uuid.UUID, file_name: str, content: bytes
) -> ImportBatch:
    batch = ImportBatch(user_id=user_id, file_name=file_name, status="PROCESSING")
    db.add(batch)
    await db.flush()

    languages = {
        lang.code: lang.id
        for lang in await db.scalars(select(Language).where(Language.user_id == user_id))
    }

    errors: list[str] = []
    imported = 0
    failed = 0
    total = 0

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        batch.status = "FAILED"
        batch.error_summary = "File is not valid UTF-8"
        await db.commit()
        await db.refresh(batch)
        return batch

    reader = csv.DictReader(io.StringIO(text))
    for row_num, row in enumerate(reader, start=2):  # row 1 = header
        total += 1
        code = (row.get("language") or "").strip()
        item_type = (row.get("item_type") or "").strip().upper()
        item_text = (row.get("text") or "").strip()

        if code not in languages:
            failed += 1
            errors.append(f"Row {row_num}: unknown language '{code}'")
            continue
        if item_type not in ("VOCABULARY", "SENTENCE"):
            failed += 1
            errors.append(f"Row {row_num}: invalid item_type '{item_type}'")
            continue
        if not item_text:
            failed += 1
            errors.append(f"Row {row_num}: text is required")
            continue

        db.add(StudyItem(
            user_id=user_id,
            language_id=languages[code],
            item_type=item_type,
            text=item_text,
            pronunciation=(row.get("pronunciation") or "").strip() or None,
            vietnamese_meaning=(row.get("vietnamese_meaning") or "").strip() or None,
            example=(row.get("example") or "").strip() or None,
            example_vietnamese=(row.get("example_vietnamese") or "").strip() or None,
            topic=(row.get("topic") or "").strip() or None,
            situation=(row.get("situation") or "").strip() or None,
            difficulty=(row.get("difficulty") or "").strip() or None,
            frequency_level=(row.get("frequency_level") or "").strip() or None,
            notes=(row.get("notes") or "").strip() or None,
            source=file_name[:120] if file_name else "import",
            source_row=row_num,
        ))
        imported += 1

    batch.total_rows = total
    batch.imported_rows = imported
    batch.failed_rows = failed
    batch.status = "COMPLETED" if failed == 0 else "COMPLETED_WITH_ERRORS"
    batch.error_summary = "\n".join(errors[:50]) or None
    batch.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(batch)
    return batch


async def export_csv(db: AsyncSession, user_id: uuid.UUID) -> str:
    rows = await db.execute(
        select(StudyItem, Language.code)
        .join(Language, StudyItem.language_id == Language.id)
        .where(StudyItem.user_id == user_id, StudyItem.is_archived.is_(False))
        .order_by(Language.code, StudyItem.created_at)
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_COLUMNS)
    for item, code in rows.all():
        writer.writerow([
            code, item.item_type, item.text, item.pronunciation or "",
            item.vietnamese_meaning or "", item.example or "",
            item.example_vietnamese or "", item.topic or "", item.situation or "",
            item.difficulty or "", item.frequency_level or "", item.notes or "",
        ])
    return output.getvalue()


async def export_backup(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Full JSON backup: languages + items with progress state."""
    languages = [
        {
            "code": lang.code, "name": lang.name, "nativeName": lang.native_name,
            "ttsLang": lang.tts_lang, "accentColor": lang.accent_color,
            "isActive": lang.is_active,
        }
        for lang in await db.scalars(select(Language).where(Language.user_id == user_id))
    ]
    items = []
    rows = await db.execute(
        select(StudyItem, Language.code)
        .join(Language, StudyItem.language_id == Language.id)
        .where(StudyItem.user_id == user_id)
    )
    for item, code in rows.all():
        items.append({
            "language": code,
            "itemType": item.item_type,
            "text": item.text,
            "pronunciation": item.pronunciation,
            "vietnameseMeaning": item.vietnamese_meaning,
            "example": item.example,
            "exampleVietnamese": item.example_vietnamese,
            "topic": item.topic,
            "situation": item.situation,
            "difficulty": item.difficulty,
            "frequencyLevel": item.frequency_level,
            "notes": item.notes,
            "timesReview": item.times_review,
            "passed": item.passed,
            "wrongCount": item.wrong_count,
            "hardLevel": item.hard_level,
            "lastDateReview": item.last_date_review.isoformat() if item.last_date_review else None,
            "nextReviewDate": item.next_review_date.isoformat() if item.next_review_date else None,
            "isArchived": item.is_archived,
        })
    return json.dumps(
        {"version": 1, "exportedAt": datetime.now(timezone.utc).isoformat(),
         "languages": languages, "items": items},
        ensure_ascii=False, indent=2,
    )
