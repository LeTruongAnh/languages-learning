"""P1 features: due forecast + emotional completion stats."""

import pytest

from tests.conftest import create_language, register_and_login

pytestmark = pytest.mark.asyncio


async def _make_item(client, headers, lang_id, text="你好") -> dict:
    res = await client.post(
        "/study-items",
        json={
            "languageId": lang_id,
            "itemType": "VOCABULARY",
            "text": text,
            "vietnameseMeaning": "xin chào",
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


async def test_dashboard_language_due_tomorrow(client):
    headers = await register_and_login(client, "fc@example.com")
    lang = await create_language(client, headers)
    await _make_item(client, headers, lang["id"], text="新")

    res = await client.get("/dashboard/languages", headers=headers)
    assert res.status_code == 200
    row = res.json()[0]
    assert "dueTomorrow" in row
    assert row["dueTomorrow"] == 0  # brand-new item has no next_review_date


async def test_completion_stats(client):
    headers = await register_and_login(client, "done@example.com")
    lang = await create_language(client, headers)
    for i in range(3):
        await _make_item(client, headers, lang["id"], text=f"词{i}")

    res = await client.post(
        f"/languages/{lang['id']}/study-sessions/daily", headers=headers
    )
    assert res.status_code == 201, res.text
    session = res.json()
    for si in session["items"]:
        r = await client.post(
            f"/study-sessions/{session['id']}/items/{si['id']}/review",
            json={"result": "GOOD"},
            headers=headers,
        )
        assert r.status_code == 200, r.text

    res = await client.post(
        f"/study-sessions/{session['id']}/complete", headers=headers
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "COMPLETED"
    assert body["streakDays"] == 1
    assert body["longestStreak"] == 1
    assert body["isNewRecord"] is False  # day one: no trivial badge
    assert isinstance(body["graduatedCount"], int)

    # Plain GET (not complete) must not carry stats.
    res = await client.get(f"/study-sessions/{session['id']}", headers=headers)
    assert res.json()["streakDays"] is None
