"""TTS endpoint: auth (header + query token), on-demand generation (mocked),
caching, cross-user isolation."""

import pytest

from app.services import tts_service
from tests.conftest import create_language, register_and_login

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def mock_generator(tmp_path, monkeypatch):
    """No network in tests: fake edge-tts by writing dummy bytes."""
    monkeypatch.setattr(
        tts_service.get_settings(), "tts_cache_dir", str(tmp_path), raising=False
    )
    calls = []

    async def fake_generate(text, tts_lang, dest):
        calls.append((text, tts_lang))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"ID3fake-mp3-bytes")

    monkeypatch.setattr(tts_service, "generate", fake_generate)
    return calls


async def make_item(client, headers, lang_id, text="你好"):
    res = await client.post(
        "/study-items",
        json={"languageId": lang_id, "itemType": "VOCABULARY", "text": text},
        headers=headers,
    )
    return res.json()["id"]


async def test_tts_generation_and_cache(client, mock_generator):
    headers = await register_and_login(client, "tts@example.com")
    lang = await create_language(client, headers, "zh")
    item_id = await make_item(client, headers, lang["id"])

    res = await client.get(f"/tts/{item_id}", headers=headers)
    assert res.status_code == 200, res.text
    assert res.headers["content-type"] == "audio/mpeg"
    assert res.content.startswith(b"ID3")
    assert len(mock_generator) == 1
    assert mock_generator[0] == ("你好", "zh-XX")

    # Second call served from cache - no regeneration
    res = await client.get(f"/tts/{item_id}", headers=headers)
    assert res.status_code == 200
    assert len(mock_generator) == 1


async def test_tts_query_token_auth(client, mock_generator):
    headers = await register_and_login(client, "ttsq@example.com")
    lang = await create_language(client, headers, "en")
    item_id = await make_item(client, headers, lang["id"], text="hello")

    token = headers["Authorization"].removeprefix("Bearer ")

    # No auth at all -> 401
    res = await client.get(f"/tts/{item_id}")
    assert res.status_code == 401

    # ?token= works (for HTML audio elements)
    res = await client.get(f"/tts/{item_id}", params={"token": token})
    assert res.status_code == 200

    # Garbage token -> 401
    res = await client.get(f"/tts/{item_id}", params={"token": "garbage"})
    assert res.status_code == 401


async def test_tts_shared_across_users(client, mock_generator):
    """Catalog audio is shared: any authenticated user can play any item."""
    headers_a = await register_and_login(client, "ttsa@example.com")
    headers_b = await register_and_login(client, "ttsb@example.com")
    lang = await create_language(client, headers_a, "zh")
    item_id = await make_item(client, headers_a, lang["id"])

    res = await client.get(f"/tts/{item_id}", headers=headers_b)
    assert res.status_code == 200


def test_voice_mapping():
    assert tts_service.voice_for("zh-CN") == "zh-CN-XiaoxiaoNeural"
    assert tts_service.voice_for("en-US") == "en-US-JennyNeural"
    assert tts_service.voice_for("zh-HK").startswith("zh-")   # prefix fallback
    assert tts_service.voice_for("xx-YY") == tts_service.DEFAULT_VOICE
