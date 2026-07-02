import pytest

from tests.conftest import create_language, register_and_login

pytestmark = pytest.mark.asyncio

CSV_OK = """language,item_type,text,pronunciation,vietnamese_meaning,example,example_vietnamese,topic,situation,difficulty,frequency_level,notes
zh,VOCABULARY,你好,nǐ hǎo,Xin chào,你好！,Xin chào!,Greetings,,Easy,High,
zh,SENTENCE,很高兴认识你,hěn gāoxìng rènshi nǐ,Rất vui được gặp bạn,,,Greetings,Meeting,Medium,,
xx,VOCABULARY,bad-lang,,,,,,,,,
zh,BADTYPE,bad-type,,,,,,,,,
zh,VOCABULARY,,,,,,,,,,
"""


async def test_csv_import_and_export(client):
    headers = await register_and_login(client, "import@example.com")
    await create_language(client, headers, "zh", "Chinese")

    res = await client.post(
        "/imports/study-items",
        files={"file": ("items.csv", CSV_OK.encode(), "text/csv")},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    batch = res.json()
    assert batch["totalRows"] == 5
    assert batch["importedRows"] == 2
    assert batch["failedRows"] == 3
    assert "unknown language 'xx'" in batch["errorSummary"]

    # Batch retrievable
    res = await client.get(f"/imports/{batch['id']}", headers=headers)
    assert res.status_code == 200

    # Items landed
    items = (await client.get("/study-items", headers=headers)).json()
    assert items["total"] == 2

    # Export CSV round-trip contains the imported item
    res = await client.get("/exports/study-items.csv", headers=headers)
    assert res.status_code == 200
    assert "你好" in res.text

    # JSON backup
    res = await client.get("/exports/backup.json", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == 1
    assert len(data["items"]) == 2


async def test_import_rejects_non_csv_and_too_large(client):
    headers = await register_and_login(client, "import2@example.com")
    res = await client.post(
        "/imports/study-items",
        files={"file": ("evil.xlsx", b"PK...", "application/octet-stream")},
        headers=headers,
    )
    assert res.status_code == 400

    big = b"a" * (5 * 1024 * 1024 + 1)
    res = await client.post(
        "/imports/study-items",
        files={"file": ("big.csv", big, "text/csv")},
        headers=headers,
    )
    assert res.status_code == 413
