"""Pre-generate TTS mp3 for ALL study items (one-time batch).

Usage (from backend/, venv active, .env configured):
    pip install edge-tts
    python scripts/generate_tts.py            # all items missing audio
    python scripts/generate_tts.py --force    # regenerate everything

Runs directly against the database (server does not need to be running).
Safe to re-run: existing files are skipped. ~30-60 min for 9.5k items.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402
from app.models import Language, StudyItem  # noqa: E402
from app.services.tts_service import audio_path, generate  # noqa: E402

CONCURRENCY = 8


async def main(force: bool) -> None:
    async with async_session_factory() as db:
        rows = (await db.execute(
            select(StudyItem.id, StudyItem.text, Language.tts_lang)
            .join(Language, StudyItem.language_id == Language.id)
            .where(StudyItem.is_archived.is_(False))
        )).all()

    todo = [r for r in rows if force or not audio_path(r.id).exists()]
    print(f"Tong items: {len(rows)} | can sinh audio: {len(todo)}")
    if not todo:
        print("Khong co gi de lam.")
        return

    sem = asyncio.Semaphore(CONCURRENCY)
    done = 0
    errors = 0

    async def worker(row):
        nonlocal done, errors
        async with sem:
            try:
                await generate(row.text, row.tts_lang, audio_path(row.id))
            except Exception as exc:
                errors += 1
                print(f"  LOI {row.text[:20]!r}: {exc}")
            finally:
                done += 1
                if done % 100 == 0:
                    print(f"  {done}/{len(todo)}...")

    await asyncio.gather(*(worker(r) for r in todo))
    print(f"XONG: {done - errors} ok, {errors} loi.")
    if errors:
        print("Chay lai script de thu lai cac file loi.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Sinh lai tat ca")
    args = parser.parse_args()
    asyncio.run(main(args.force))
