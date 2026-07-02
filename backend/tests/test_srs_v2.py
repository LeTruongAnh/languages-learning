"""SRS v2: 4 grades with ease factor, undo, direction + reminder settings."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from tests.conftest import create_language, register_and_login

pytestmark = pytest.mark.asyncio


def user_today() -> date:
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()


async def setup_session(client, email, vocab=2):
    headers = await register_and_login(client, email)
    lang = await create_language(client, headers, "zh")
    await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"dailyLimit": vocab, "vocabularyRatio": "1.0", "sentenceRatio": "0.0"},
        headers=headers,
    )
    for i in range(vocab):
        await client.post(
            "/study-items",
            json={"languageId": lang["id"], "itemType": "VOCABULARY", "text": f"w{i}"},
            headers=headers,
        )
    session = (await client.post(
        f"/languages/{lang['id']}/study-sessions/daily", headers=headers
    )).json()
    return headers, lang, session


async def test_grades_ease_and_intervals(client):
    headers, lang, session = await setup_session(client, "grades@example.com", vocab=3)
    today = user_today()
    items = session["items"]

    # EASY on first review: interval = base(1) * 2, ease 2.5 -> 2.65
    res = (await client.post(
        f"/study-sessions/{session['id']}/items/{items[0]['id']}/review",
        json={"result": "EASY"}, headers=headers)).json()
    p = res["newProgress"]
    assert p["timesReview"] == 1
    assert float(p["ease"]) == 2.65
    assert p["intervalDays"] == 2
    assert p["nextReviewDate"] == (today + timedelta(days=2)).isoformat()

    # HARD on first review: interval = base(1), ease 2.5 -> 2.35
    res = (await client.post(
        f"/study-sessions/{session['id']}/items/{items[1]['id']}/review",
        json={"result": "HARD"}, headers=headers)).json()
    p = res["newProgress"]
    assert float(p["ease"]) == 2.35
    assert p["intervalDays"] == 1

    # AGAIN: reset, wrong+1, ease 2.5 -> 2.30, next = tomorrow
    res = (await client.post(
        f"/study-sessions/{session['id']}/items/{items[2]['id']}/review",
        json={"result": "AGAIN"}, headers=headers)).json()
    p = res["newProgress"]
    assert p["timesReview"] == 0
    assert p["wrongCount"] == 1
    assert float(p["ease"]) == 2.30
    assert p["nextReviewDate"] == (today + timedelta(days=1)).isoformat()

    # Legacy alias still accepted and normalized
    sp = res["sessionProgress"]
    assert sp["passCount"] == 2 and sp["failCount"] == 1


async def test_interval_growth_with_ease(client):
    from app.services.review_service import apply_ease, compute_interval

    # ease clamping
    assert apply_ease(2.5, "EASY") == 2.65
    assert apply_ease(2.95, "EASY") == 3.0
    assert apply_ease(1.35, "AGAIN") == 1.3
    # multiplicative growth from previous interval
    assert compute_interval("GOOD", 3, 2.5, 2, [1, 3, 7]) == 8   # round(3*2.5)
    assert compute_interval("HARD", 10, 2.5, 2, [1, 3, 7]) == 12  # x1.2
    assert compute_interval("EASY", 3, 2.5, 2, [1, 3, 7]) == 10   # round(3*2.5*1.3)
    # first review uses base intervals
    assert compute_interval("GOOD", 0, 2.5, 1, [1, 3, 7]) == 1
    assert compute_interval("EASY", 0, 2.5, 1, [1, 3, 7]) == 2


async def test_undo_flow(client):
    headers, lang, session = await setup_session(client, "undo@example.com", vocab=2)
    a, b = session["items"]

    # Cannot undo an unanswered card
    res = await client.post(
        f"/study-sessions/{session['id']}/items/{a['id']}/undo", headers=headers)
    assert res.status_code == 409

    # Answer A (GOOD) then B (AGAIN)
    await client.post(
        f"/study-sessions/{session['id']}/items/{a['id']}/review",
        json={"result": "GOOD"}, headers=headers)
    await client.post(
        f"/study-sessions/{session['id']}/items/{b['id']}/review",
        json={"result": "AGAIN"}, headers=headers)

    # A is not the latest anymore -> 409
    res = await client.post(
        f"/study-sessions/{session['id']}/items/{a['id']}/undo", headers=headers)
    assert res.status_code == 409

    # Undo B: item fully restored, counters rolled back
    res = await client.post(
        f"/study-sessions/{session['id']}/items/{b['id']}/undo", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["undoneResult"] == "AGAIN"
    restored = body["restored"]
    assert restored["timesReview"] == 0
    assert restored["wrongCount"] == 0
    assert float(restored["ease"]) == 2.5
    assert restored["nextReviewDate"] is None
    sp = body["sessionProgress"]
    assert sp["completedItems"] == 1 and sp["failCount"] == 0

    # Item state in DB is clean
    item = (await client.get(f"/study-items/{body['studyItemId']}", headers=headers)).json()
    assert item["timesReview"] == 0 and item["wrongCount"] == 0

    # Card can be answered again with a different grade
    res = (await client.post(
        f"/study-sessions/{session['id']}/items/{b['id']}/review",
        json={"result": "EASY"}, headers=headers)).json()
    assert res["newProgress"]["timesReview"] == 1
    assert res["sessionProgress"]["completedItems"] == 2

    # After completing the session, undo is blocked
    await client.post(f"/study-sessions/{session['id']}/complete", headers=headers)
    res = await client.post(
        f"/study-sessions/{session['id']}/items/{b['id']}/undo", headers=headers)
    assert res.status_code == 409


async def test_undo_cross_user_isolation(client):
    headers_a, lang, session = await setup_session(client, "undoa@example.com", vocab=1)
    headers_b = await register_and_login(client, "undob@example.com")
    si = session["items"][0]
    await client.post(
        f"/study-sessions/{session['id']}/items/{si['id']}/review",
        json={"result": "GOOD"}, headers=headers_a)
    res = await client.post(
        f"/study-sessions/{session['id']}/items/{si['id']}/undo", headers=headers_b)
    assert res.status_code == 404


async def test_direction_and_reminder_settings(client):
    headers = await register_and_login(client, "dir@example.com")
    lang = await create_language(client, headers, "zh")

    settings = (await client.get(f"/languages/{lang['id']}/settings", headers=headers)).json()
    assert settings["studyDirection"] == "FRONT"

    res = await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"studyDirection": "MIXED"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["studyDirection"] == "MIXED"

    res = await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"studyDirection": "UPSIDE_DOWN"}, headers=headers)
    assert res.status_code == 422

    # Reminder settings
    us = (await client.get("/user-settings", headers=headers)).json()
    assert us["reminderEnabled"] is False and us["reminderHour"] == 20
    res = await client.patch(
        "/user-settings", json={"reminderEnabled": True, "reminderHour": 7}, headers=headers)
    assert res.json()["reminderHour"] == 7
    res = await client.patch("/user-settings", json={"reminderHour": 99}, headers=headers)
    assert res.status_code == 422
