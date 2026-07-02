"""Server-side TTS via edge-tts (Microsoft Edge neural voices).

Why: on-device/browser TTS (flutter_tts / Web Speech API) is inconsistent
across devices and buggy on Chrome. The vocabulary set is fixed, so we
generate each item's audio ONCE, cache it as mp3, and the app just plays a
file - identical voice everywhere, no engine quirks.

edge-tts uses unofficial Edge endpoints (free, no key). If it ever breaks,
swap generate() to Azure Speech - the voice names are identical.
"""

import asyncio
import uuid
from pathlib import Path

from app.core.config import get_settings

# tts_lang (languages.tts_lang) -> Edge neural voice
VOICE_MAP = {
    "zh-CN": "zh-CN-XiaoxiaoNeural",
    "zh-TW": "zh-TW-HsiaoChenNeural",
    "en-US": "en-US-JennyNeural",
    "en-GB": "en-GB-SoniaNeural",
    "ja-JP": "ja-JP-NanamiNeural",
    "ko-KR": "ko-KR-SunHiNeural",
    "fr-FR": "fr-FR-DeniseNeural",
    "vi-VN": "vi-VN-HoaiMyNeural",
}
DEFAULT_VOICE = "en-US-JennyNeural"

# Serialize generation a bit so on-demand requests don't stampede.
_gen_semaphore = asyncio.Semaphore(4)


def voice_for(tts_lang: str) -> str:
    if tts_lang in VOICE_MAP:
        return VOICE_MAP[tts_lang]
    # Fallback by language prefix (e.g. "zh-HK" -> first zh-* voice)
    prefix = tts_lang.split("-")[0].lower()
    for lang, voice in VOICE_MAP.items():
        if lang.lower().startswith(prefix):
            return voice
    return DEFAULT_VOICE


def audio_path(item_id: uuid.UUID) -> Path:
    return Path(get_settings().tts_cache_dir) / f"{item_id}.mp3"


async def generate(text: str, tts_lang: str, dest: Path) -> None:
    """Generate one mp3. Import inside the function so the app can run
    (and tests can mock this) without the edge-tts package/network."""
    import edge_tts

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    communicate = edge_tts.Communicate(text, voice_for(tts_lang))
    await communicate.save(str(tmp))
    tmp.rename(dest)  # atomic-ish: never serve half-written files


async def get_or_generate(item_id: uuid.UUID, text: str, tts_lang: str) -> Path:
    """Return the cached mp3 path, generating it on first request."""
    path = audio_path(item_id)
    if path.exists() and path.stat().st_size > 0:
        return path
    async with _gen_semaphore:
        if not path.exists():  # re-check after waiting on the semaphore
            await generate(text, tts_lang, path)
    return path
