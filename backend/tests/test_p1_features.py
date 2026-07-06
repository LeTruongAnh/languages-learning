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


async def _enroll(client, headers, lang_id):
    r = await client.put(
        "/languages/enrollments", json={"languageIds": [lang_id]}, headers=headers
    )
    assert r.status_code == 200, r.text


async def test_dashboard_language_due_tomorrow(client):
    headers = await register_and_login(client, "fc@example.com")
    lang = await create_language(client, headers)
    await _enroll(client, headers, lang["id"])
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


async def test_active_session_surfaces_on_dashboard(client):
    """Pausing a session must NOT lose it: dashboard reports the unfinished
    session so Home can resume instead of spawning a new one."""
    headers = await register_and_login(client, "resume@example.com")
    lang = await create_language(client, headers)
    await _enroll(client, headers, lang["id"])
    for i in range(3):
        await _make_item(client, headers, lang["id"], text=f"字{i}")

    # No session yet -> nothing to resume.
    res = await client.get("/dashboard/languages", headers=headers)
    assert res.json()[0]["activeSessionType"] is None

    # Start a daily session, answer ONE card, then "pause" (just leave).
    res = await client.post(
        f"/languages/{lang['id']}/study-sessions/daily", headers=headers
    )
    session = res.json()
    await client.post(
        f"/study-sessions/{session['id']}/items/{session['items'][0]['id']}/review",
        json={"result": "GOOD"},
        headers=headers,
    )
    res = await client.get("/dashboard/languages", headers=headers)
    assert res.json()[0]["activeSessionType"] == "LANGUAGE_DAILY"

    # The resume endpoint returns THAT session with progress intact.
    res = await client.get(
        f"/languages/{lang['id']}/study-sessions/current", headers=headers
    )
    assert res.status_code == 200
    assert res.json()["id"] == session["id"]
    assert res.json()["completedItems"] == 1

    # Completing it clears the resume state.
    res = await client.post(
        f"/study-sessions/{session['id']}/complete", headers=headers
    )
    assert res.status_code == 200
    res = await client.get("/dashboard/languages", headers=headers)
    assert res.json()[0]["activeSessionType"] is None


async def test_non_admin_cannot_write_catalog(client, monkeypatch):
    """Catalog writes are admin-only; regular users get 403."""
    from app.core.config import get_settings as cfg

    headers_admin = await register_and_login(client, "boss@example.com")
    lang = await create_language(client, headers_admin)
    item = await _make_item(client, headers_admin, lang["id"])

    monkeypatch.setattr(cfg(), "admin_emails", "boss@example.com")
    headers_user = await register_and_login(client, "pleb@example.com")

    r = await client.post(
        "/study-items",
        json={"languageId": lang["id"], "itemType": "VOCABULARY", "text": "x"},
        headers=headers_user,
    )
    assert r.status_code == 403
    assert (await client.patch(
        f"/study-items/{item['id']}", json={"text": "y"}, headers=headers_user
    )).status_code == 403
    assert (await client.delete(
        f"/study-items/{item['id']}", headers=headers_user
    )).status_code == 403
    assert (await client.post(
        "/languages", json={"code": "fr", "name": "French", "ttsLang": "fr-FR"},
        headers=headers_user,
    )).status_code == 403
    # But the user READS the catalog + studies it normally.
    assert (await client.get("/study-items", headers=headers_user)).json()["total"] == 1
    r = await client.post(
        f"/languages/{lang['id']}/study-sessions/daily", headers=headers_user
    )
    assert r.status_code == 201 and len(r.json()["items"]) == 1


async def test_enrollment_flow(client):
    """Register -> empty home -> choose languages -> unenroll keeps progress."""
    admin = await register_and_login(client, "cat-admin@example.com")
    lang = await create_language(client, admin, "zh", "Chinese")
    await create_language(client, admin, "en", "English")
    await _make_item(client, admin, lang["id"], text="你好")

    user = await register_and_login(client, "newbie@example.com")
    # Fresh account: catalog visible, nothing enrolled, Home empty.
    langs = (await client.get("/languages", headers=user)).json()
    assert len(langs) == 2 and all(l["enrolled"] is False for l in langs)
    assert (await client.get("/dashboard/languages", headers=user)).json() == []

    # Enroll Chinese only.
    r = await client.put(
        "/languages/enrollments", json={"languageIds": [lang["id"]]}, headers=user
    )
    assert r.status_code == 200 and r.json()[0]["enrolled"] is True
    home = (await client.get("/dashboard/languages", headers=user)).json()
    assert [l["code"] for l in home] == ["zh"]

    # Study one card, then UN-enroll -> hidden but progress kept.
    s = (await client.post(
        f"/languages/{lang['id']}/study-sessions/daily", headers=user
    )).json()
    await client.post(
        f"/study-sessions/{s['id']}/items/{s['items'][0]['id']}/review",
        json={"result": "GOOD"}, headers=user,
    )
    await client.put("/languages/enrollments", json={"languageIds": []}, headers=user)
    assert (await client.get("/dashboard/languages", headers=user)).json() == []
    # Re-enroll: progress still there.
    await client.put(
        "/languages/enrollments", json={"languageIds": [lang["id"]]}, headers=user
    )
    item_id = s["items"][0]["item"]["id"]
    assert (await client.get(
        f"/study-items/{item_id}", headers=user
    )).json()["timesReview"] == 1
