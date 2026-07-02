import pytest

from tests.conftest import create_language, register_and_login

pytestmark = pytest.mark.asyncio


async def test_language_crud_and_settings(client):
    headers = await register_and_login(client, "lang@example.com")

    lang = await create_language(client, headers, "zh", "Chinese")
    assert lang["code"] == "zh"

    # Default settings auto-created
    res = await client.get(f"/languages/{lang['id']}/settings", headers=headers)
    assert res.status_code == 200
    settings = res.json()
    assert settings["dailyLimit"] == 20
    assert settings["reviewIntervals"] == [1, 3, 7]

    # Update settings with valid ratios
    res = await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"dailyLimit": 10, "vocabularyRatio": "0.8", "sentenceRatio": "0.2"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["dailyLimit"] == 10

    # Invalid: ratios don't sum to 1
    res = await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"vocabularyRatio": "0.8", "sentenceRatio": "0.8"},
        headers=headers,
    )
    assert res.status_code == 422

    # Invalid: dailyLimit out of range (spec §13.2)
    res = await client.patch(
        f"/languages/{lang['id']}/settings", json={"dailyLimit": 500}, headers=headers
    )
    assert res.status_code == 422

    # Soft delete
    res = await client.delete(f"/languages/{lang['id']}", headers=headers)
    assert res.status_code == 204
    res = await client.get("/languages", headers=headers)
    assert res.json() == []

    # Re-creating same code reactivates it
    res = await client.post(
        "/languages", json={"code": "zh", "name": "Chinese", "ttsLang": "zh-CN"},
        headers=headers,
    )
    assert res.status_code == 201


async def test_duplicate_language_code_conflict(client):
    headers = await register_and_login(client, "dup@example.com")
    await create_language(client, headers, "en", "English")
    res = await client.post(
        "/languages", json={"code": "en", "name": "English 2", "ttsLang": "en-US"},
        headers=headers,
    )
    assert res.status_code == 409


async def test_cross_user_isolation(client):
    """User B must never see or touch user A's data — returns 404, not 403."""
    headers_a = await register_and_login(client, "isola@example.com")
    headers_b = await register_and_login(client, "isolb@example.com")

    lang_a = await create_language(client, headers_a, "zh", "Chinese")

    # B cannot read A's language, settings, or delete it
    assert (await client.get(f"/languages/{lang_a['id']}", headers=headers_b)).status_code == 404
    assert (
        await client.get(f"/languages/{lang_a['id']}/settings", headers=headers_b)
    ).status_code == 404
    assert (
        await client.delete(f"/languages/{lang_a['id']}", headers=headers_b)
    ).status_code == 404

    # A's item invisible to B
    item = await client.post(
        "/study-items",
        json={"languageId": lang_a["id"], "itemType": "VOCABULARY", "text": "你好"},
        headers=headers_a,
    )
    item_id = item.json()["id"]
    assert (await client.get(f"/study-items/{item_id}", headers=headers_b)).status_code == 404
    body = (await client.get("/study-items", headers=headers_b)).json()
    assert body["total"] == 0

    # B cannot create an item inside A's language
    res = await client.post(
        "/study-items",
        json={"languageId": lang_a["id"], "itemType": "VOCABULARY", "text": "hack"},
        headers=headers_b,
    )
    assert res.status_code == 404
