"""End-to-end study engine tests: session generation, review algorithm,
idempotency, hard items, dashboard."""

from datetime import date, timedelta
from zoneinfo import ZoneInfo
from datetime import datetime

import pytest

from tests.conftest import create_language, register_and_login

pytestmark = pytest.mark.asyncio


def user_today() -> date:
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()


async def seed_items(client, headers, language_id, vocab=0, sentences=0):
    for i in range(vocab):
        res = await client.post(
            "/study-items",
            json={
                "languageId": language_id, "itemType": "VOCABULARY",
                "text": f"vocab-{i}", "vietnameseMeaning": f"nghĩa {i}",
            },
            headers=headers,
        )
        assert res.status_code == 201
    for i in range(sentences):
        res = await client.post(
            "/study-items",
            json={
                "languageId": language_id, "itemType": "SENTENCE",
                "text": f"sentence-{i}", "vietnameseMeaning": f"câu {i}",
            },
            headers=headers,
        )
        assert res.status_code == 201


async def test_daily_session_ratio_and_ordering(client):
    headers = await register_and_login(client, "engine@example.com")
    lang = await create_language(client, headers, "zh")
    await seed_items(client, headers, lang["id"], vocab=30, sentences=10)

    res = await client.post(f"/languages/{lang['id']}/study-sessions/daily", headers=headers)
    assert res.status_code == 201
    session = res.json()

    # daily_limit 20, vocab ratio 0.7 -> 14 vocab / 6 sentence (spec §2.2)
    assert session["totalItems"] == 20
    buckets = [i["plannedBucket"] for i in session["items"]]
    assert sum(b.startswith("VOCAB") for b in buckets) == 14
    assert sum(b.startswith("SENTENCE") for b in buckets) == 6

    # Ordering: all vocab blocks before all sentence blocks (spec §9.5)
    first_sentence = next(i for i, b in enumerate(buckets) if b.startswith("SENTENCE"))
    assert all(not b.startswith("VOCAB") for b in buckets[first_sentence:])

    # Idempotent: calling daily again returns the same session
    res2 = await client.post(f"/languages/{lang['id']}/study-sessions/daily", headers=headers)
    assert res2.json()["id"] == session["id"]

    # current returns it too
    res3 = await client.get(
        f"/languages/{lang['id']}/study-sessions/current", headers=headers
    )
    assert res3.json()["id"] == session["id"]


async def test_review_pass_fail_skip_algorithm(client):
    headers = await register_and_login(client, "algo@example.com")
    lang = await create_language(client, headers, "en")
    # Small session: 2 vocab items only
    await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"dailyLimit": 2, "vocabularyRatio": "1.0", "sentenceRatio": "0.0"},
        headers=headers,
    )
    await seed_items(client, headers, lang["id"], vocab=2)

    session = (await client.post(
        f"/languages/{lang['id']}/study-sessions/daily", headers=headers
    )).json()
    assert session["totalItems"] == 2
    si_pass, si_fail = session["items"][0], session["items"][1]
    today = user_today()

    # PASS: times 0->1, next = today + intervals[0] = +1 day (spec §8.1)
    res = await client.post(
        f"/study-sessions/{session['id']}/items/{si_pass['id']}/review",
        json={"result": "PASS"}, headers=headers,
    )
    assert res.status_code == 200
    prog = res.json()["newProgress"]
    assert prog["timesReview"] == 1
    assert prog["passed"] is False
    assert prog["nextReviewDate"] == (today + timedelta(days=1)).isoformat()

    # Idempotency: resubmitting the same session item does NOT re-apply (spec §12.4)
    res2 = await client.post(
        f"/study-sessions/{session['id']}/items/{si_pass['id']}/review",
        json={"result": "PASS"}, headers=headers,
    )
    assert res2.json()["alreadyApplied"] is True
    assert res2.json()["newProgress"]["timesReview"] == 1

    # FAIL: times reset, wrong+1, next = tomorrow
    res = await client.post(
        f"/study-sessions/{session['id']}/items/{si_fail['id']}/review",
        json={"result": "FAIL"}, headers=headers,
    )
    prog = res.json()["newProgress"]
    assert prog["timesReview"] == 0
    assert prog["wrongCount"] == 1
    assert prog["hardLevel"] == "Normal"
    assert prog["nextReviewDate"] == (today + timedelta(days=1)).isoformat()

    sp = res.json()["sessionProgress"]
    assert sp["completedItems"] == 2
    assert sp["passCount"] == 1 and sp["failCount"] == 1

    # Complete session
    res = await client.post(f"/study-sessions/{session['id']}/complete", headers=headers)
    assert res.json()["status"] == "COMPLETED"

    # Reviewing a completed session -> 409
    res = await client.post(
        f"/study-sessions/{session['id']}/items/{si_fail['id']}/review",
        json={"result": "PASS"}, headers=headers,
    )
    assert res.status_code == 409


async def test_hard_level_escalation_and_hard_session(client):
    headers = await register_and_login(client, "hard@example.com")
    lang = await create_language(client, headers, "zh")
    await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"dailyLimit": 1, "vocabularyRatio": "1.0", "sentenceRatio": "0.0",
              "avoidSameDayRepeat": False},
        headers=headers,
    )
    await seed_items(client, headers, lang["id"], vocab=1)

    # FAIL twice via daily + extra session (same item allowed: avoidSameDayRepeat off,
    # but item next_review = tomorrow after fail -> use extra sessions picking NEW/REVIEW.
    session = (await client.post(
        f"/languages/{lang['id']}/study-sessions/daily", headers=headers
    )).json()
    res = await client.post(
        f"/study-sessions/{session['id']}/items/{session['items'][0]['id']}/review",
        json={"result": "FAIL"}, headers=headers,
    )
    assert res.json()["newProgress"]["wrongCount"] == 1

    # wrong_count >= 2 => Hard (spec §8.2) — simulate by failing again tomorrow;
    # here we check the pure function instead.
    from app.services.review_service import compute_hard_level, next_interval_days

    assert compute_hard_level(0) == "Normal"
    assert compute_hard_level(2) == "Hard"
    assert compute_hard_level(3) == "Very Hard"
    assert compute_hard_level(10) == "Very Hard"

    # Interval clamping (PLAN.md §1.2#4)
    assert next_interval_days([1, 3, 7], 1) == 1
    assert next_interval_days([1, 3, 7], 2) == 3
    assert next_interval_days([1, 3, 7], 3) == 7
    assert next_interval_days([1, 3, 7], 99) == 7  # clamp
    assert next_interval_days([], 1) == 1  # fallback

    # No hard items yet -> 404
    res = await client.post("/hard-items/study-sessions", headers=headers)
    assert res.status_code == 404


async def test_skip_does_not_change_progress(client):
    headers = await register_and_login(client, "skip@example.com")
    lang = await create_language(client, headers, "en")
    await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"dailyLimit": 1, "vocabularyRatio": "1.0", "sentenceRatio": "0.0"},
        headers=headers,
    )
    await seed_items(client, headers, lang["id"], vocab=1)
    session = (await client.post(
        f"/languages/{lang['id']}/study-sessions/daily", headers=headers
    )).json()

    res = await client.post(
        f"/study-sessions/{session['id']}/items/{session['items'][0]['id']}/review",
        json={"result": "SKIP"}, headers=headers,
    )
    prog = res.json()["newProgress"]
    assert prog["timesReview"] == 0
    assert prog["wrongCount"] == 0
    assert prog["nextReviewDate"] is None
    assert res.json()["sessionProgress"]["skipCount"] == 1

    # Item state untouched in DB
    item_id = res.json()["studyItemId"]
    item = (await client.get(f"/study-items/{item_id}", headers=headers)).json()
    assert item["timesReview"] == 0
    assert item["lastDateReview"] is None


async def test_dashboard_and_history(client):
    headers = await register_and_login(client, "dash@example.com")
    lang = await create_language(client, headers, "zh")
    await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"dailyLimit": 2, "vocabularyRatio": "1.0", "sentenceRatio": "0.0"},
        headers=headers,
    )
    await seed_items(client, headers, lang["id"], vocab=2)
    session = (await client.post(
        f"/languages/{lang['id']}/study-sessions/daily", headers=headers
    )).json()
    for si, result in zip(session["items"], ("PASS", "FAIL")):
        await client.post(
            f"/study-sessions/{session['id']}/items/{si['id']}/review",
            json={"result": result}, headers=headers,
        )

    summary = (await client.get("/dashboard/summary", headers=headers)).json()
    assert summary["todayLearned"] == 2
    assert summary["passCount"] == 1
    assert summary["failCount"] == 1
    assert summary["passRate"] == 0.5
    assert summary["streakDays"] == 1
    assert summary["dueToday"] == 0  # both moved to tomorrow/next interval

    langs = (await client.get("/dashboard/languages", headers=headers)).json()
    assert len(langs) == 1
    assert langs[0]["todayLearned"] == 2
    assert langs[0]["dailyLimit"] == 2

    history = (await client.get("/dashboard/history?range=7d", headers=headers)).json()
    assert len(history) == 1
    assert history[0]["learned"] == 2


async def test_session_isolation_between_users(client):
    headers_a = await register_and_login(client, "sessa@example.com")
    headers_b = await register_and_login(client, "sessb@example.com")
    lang = await create_language(client, headers_a, "zh")
    await seed_items(client, headers_a, lang["id"], vocab=1)
    session = (await client.post(
        f"/languages/{lang['id']}/study-sessions/daily", headers=headers_a
    )).json()

    # B cannot read A's session nor submit reviews into it
    res = await client.get(f"/study-sessions/{session['id']}", headers=headers_b)
    assert res.status_code == 404
    res = await client.post(
        f"/study-sessions/{session['id']}/items/{session['items'][0]['id']}/review",
        json={"result": "PASS"}, headers=headers_b,
    )
    assert res.status_code == 404
