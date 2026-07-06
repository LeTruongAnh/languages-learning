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
    """CATALOG is shared (reads = 200 for everyone); what stays isolated is
    per-user PROGRESS: B grading a card must not touch A's progress."""
    headers_a = await register_and_login(client, "isola@example.com")
    headers_b = await register_and_login(client, "isolb@example.com")

    lang_a = await create_language(client, headers_a, "zh", "Chinese")

    # Shared catalog: B can read the language and its items.
    assert (await client.get(f"/languages/{lang_a['id']}", headers=headers_b)).status_code == 200
    item = await client.post(
        "/study-items",
        json={"languageId": lang_a["id"], "itemType": "VOCABULARY", "text": "你好"},
        headers=headers_a,
    )
    item_id = item.json()["id"]
    assert (await client.get(f"/study-items/{item_id}", headers=headers_b)).status_code == 200
    assert (await client.get("/study-items", headers=headers_b)).json()["total"] == 1

    # PROGRESS isolation: B studies the shared card...
    res = await client.post(f"/languages/{lang_a['id']}/study-sessions/daily", headers=headers_b)
    session = res.json()
    await client.post(
        f"/study-sessions/{session['id']}/items/{session['items'][0]['id']}/review",
        json={"result": "GOOD"},
        headers=headers_b,
    )
    # ...B sees progress, A still sees a fresh card.
    b_view = (await client.get(f"/study-items/{item_id}", headers=headers_b)).json()
    a_view = (await client.get(f"/study-items/{item_id}", headers=headers_a)).json()
    assert b_view["timesReview"] == 1
    assert a_view["timesReview"] == 0

    # B cannot touch A's SESSION (still 404 — sessions are per-user).
    res_a = await client.post(f"/languages/{lang_a['id']}/study-sessions/daily", headers=headers_a)
    assert (
        await client.get(f"/study-sessions/{res_a.json()['id']}", headers=headers_b)
    ).status_code == 404
