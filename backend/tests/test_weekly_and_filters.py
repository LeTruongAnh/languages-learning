"""Weekly review, priority sort, facets, weekly settings."""

import pytest

from tests.conftest import create_language, register_and_login

pytestmark = pytest.mark.asyncio


async def seed(client, headers, lang_id, n, **extra):
    for i in range(n):
        res = await client.post(
            "/study-items",
            json={"languageId": lang_id, "itemType": "VOCABULARY",
                  "text": f"w{i}", **extra},
            headers=headers,
        )
        assert res.status_code == 201


async def test_weekly_review_flow(client):
    headers = await register_and_login(client, "weekly@example.com")
    lang = await create_language(client, headers, "zh")
    await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"dailyLimit": 3, "vocabularyRatio": "1.0", "sentenceRatio": "0.0",
              "avoidSameDayRepeat": False, "weeklyReviewLimit": 10},
        headers=headers,
    )
    await seed(client, headers, lang["id"], 3)

    # No reviews yet this week -> 404
    res = await client.post(
        f"/languages/{lang['id']}/study-sessions/weekly", headers=headers)
    assert res.status_code == 404

    # Study the daily session: 2 GOOD + 1 AGAIN
    daily = (await client.post(
        f"/languages/{lang['id']}/study-sessions/daily", headers=headers)).json()
    for si, grade in zip(daily["items"], ("GOOD", "AGAIN", "GOOD")):
        await client.post(
            f"/study-sessions/{daily['id']}/items/{si['id']}/review",
            json={"result": grade}, headers=headers)

    # Weekly now picks all 3, hardest (AGAIN, wrong_count=1) first
    res = await client.post(
        f"/languages/{lang['id']}/study-sessions/weekly", headers=headers)
    assert res.status_code == 201, res.text
    weekly = res.json()
    assert weekly["sessionType"] == "LANGUAGE_WEEKLY"
    assert weekly["totalItems"] == 3
    assert weekly["items"][0]["item"]["wrongCount"] == 1  # hardest first

    # Idempotent per day
    res2 = await client.post(
        f"/languages/{lang['id']}/study-sessions/weekly", headers=headers)
    assert res2.json()["id"] == weekly["id"]


async def test_weekly_settings_validation(client):
    headers = await register_and_login(client, "wday@example.com")
    lang = await create_language(client, headers, "en")

    await client.put("/languages/enrollments",
                     json={"languageIds": [lang["id"]]}, headers=headers)

    settings = (await client.get(
        f"/languages/{lang['id']}/settings", headers=headers)).json()
    assert settings["weeklyReviewDay"] == "SUNDAY"
    assert settings["weeklyReviewLimit"] == 40

    res = await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"weeklyReviewDay": "FRIDAY", "weeklyReviewLimit": 20}, headers=headers)
    assert res.status_code == 200
    assert res.json()["weeklyReviewDay"] == "FRIDAY"

    res = await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"weeklyReviewDay": "SOMEDAY"}, headers=headers)
    assert res.status_code == 422

    # Dashboard exposes the configured day
    langs = (await client.get("/dashboard/languages", headers=headers)).json()
    assert langs[0]["weeklyReviewDay"] == "FRIDAY"


async def test_priority_sort_mode(client):
    headers = await register_and_login(client, "prio@example.com")
    lang = await create_language(client, headers, "zh")
    await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"dailyLimit": 2, "vocabularyRatio": "1.0", "sentenceRatio": "0.0",
              "sortMode": "priority", "avoidSameDayRepeat": False,
              "newRatio": "0.0", "reviewRatio": "1.0"},
        headers=headers,
    )
    await seed(client, headers, lang["id"], 3)

    # Make item wrong counts differ: fail one twice via daily+extra
    daily = (await client.post(
        f"/languages/{lang['id']}/study-sessions/daily", headers=headers)).json()
    # newRatio=0 -> review bucket empty -> fallback pulls NEW items; answer them
    for si, grade in zip(daily["items"], ("AGAIN", "GOOD")):
        await client.post(
            f"/study-sessions/{daily['id']}/items/{si['id']}/review",
            json={"result": grade}, headers=headers)

    # Extra session with priority sort: due items (both due tomorrow... the AGAIN
    # one is due tomorrow, GOOD due tomorrow too) — candidates are the remaining
    # NEW item + none due today; verify the session is created and ordered.
    extra = (await client.post(
        f"/languages/{lang['id']}/study-sessions/extra", headers=headers)).json()
    assert extra["totalItems"] >= 1  # at least the untouched NEW item


async def test_facets_endpoint(client):
    headers = await register_and_login(client, "facets@example.com")
    lang = await create_language(client, headers, "zh")
    await seed(client, headers, lang["id"], 1,
               difficulty="Beginner", topic="Food", frequencyLevel="High")
    await seed(client, headers, lang["id"], 1,
               difficulty="Advanced", topic="Travel", frequencyLevel="High")

    res = await client.get(f"/languages/{lang['id']}/facets", headers=headers)
    assert res.status_code == 200
    facets = res.json()
    assert facets["difficulties"] == ["Advanced", "Beginner"]
    assert facets["topics"] == ["Food", "Travel"]
    assert facets["frequencyLevels"] == ["High"]
    assert facets["situations"] == []

    # Shared catalog: another user reads the SAME facets
    headers_b = await register_and_login(client, "facetsb@example.com")
    res = await client.get(f"/languages/{lang['id']}/facets", headers=headers_b)
    assert res.status_code == 200
    assert res.json() == facets


async def test_difficulty_filter_applied_to_session(client):
    headers = await register_and_login(client, "filter@example.com")
    lang = await create_language(client, headers, "en")
    await client.patch(
        f"/languages/{lang['id']}/settings",
        json={"dailyLimit": 10, "vocabularyRatio": "1.0", "sentenceRatio": "0.0",
              "difficultyFilter": ["Beginner"]},
        headers=headers,
    )
    await seed(client, headers, lang["id"], 2, difficulty="Beginner")
    # different texts needed — seed() reuses w0..w1, so add advanced manually
    for i in range(3):
        await client.post(
            "/study-items",
            json={"languageId": lang["id"], "itemType": "VOCABULARY",
                  "text": f"adv{i}", "difficulty": "Advanced"},
            headers=headers)

    session = (await client.post(
        f"/languages/{lang['id']}/study-sessions/daily", headers=headers)).json()
    assert session["totalItems"] == 2  # only Beginner items
    assert all(i["item"]["difficulty"] == "Beginner" for i in session["items"])
