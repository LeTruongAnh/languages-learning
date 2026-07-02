"""Seed the database with the Chinese/English datasets + a test account.

Prerequisites: API server running (uvicorn app.main:app), CSVs in seed_data/.
Usage (from backend/, venv active):
    python scripts/seed.py
Override defaults via env: API_URL, SEED_EMAIL, SEED_PASSWORD
"""

import os
import sys
from pathlib import Path

import httpx

API = os.environ.get("API_URL", "http://localhost:8000/api")
EMAIL = os.environ.get("SEED_EMAIL", "thanhphongnguyen3005@gmail.com")
PASSWORD = os.environ.get("SEED_PASSWORD", "Vocab2026!")
SEED_DIR = Path(__file__).resolve().parent.parent / "seed_data"

LANGUAGES = [
    {"code": "zh", "name": "Chinese", "nativeName": "中文", "ttsLang": "zh-CN",
     "accentColor": "#E0533D", "sortOrder": 1, "csv": "chinese_seed.csv"},
    {"code": "en", "name": "English", "nativeName": "English", "ttsLang": "en-US",
     "accentColor": "#2563EB", "sortOrder": 2, "csv": "english_seed.csv"},
]


def main() -> None:
    client = httpx.Client(base_url=API, timeout=300)

    # Health check first
    try:
        client.get("/health").raise_for_status()
    except Exception:
        sys.exit(f"LOI: khong ket noi duoc {API} - hay chay server truoc:\n"
                 "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")

    # 1. Register (409 = already exists -> fine)
    res = client.post("/auth/register", json={
        "email": EMAIL, "password": PASSWORD, "displayName": "Phong"})
    if res.status_code == 201:
        print(f"[1/4] Da tao tai khoan {EMAIL}")
    elif res.status_code == 409:
        print(f"[1/4] Tai khoan {EMAIL} da ton tai - dung tiep")
    else:
        sys.exit(f"LOI register: {res.status_code} {res.text}")

    # 2. Login
    res = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if res.status_code != 200:
        sys.exit(f"LOI login: {res.status_code} {res.text}\n"
                 "Neu tai khoan da ton tai voi mat khau khac, dat SEED_PASSWORD cho dung.")
    client.headers["Authorization"] = f"Bearer {res.json()['accessToken']}"
    print("[2/4] Dang nhap OK")

    # 3. Create languages (409 -> already there)
    for lang in LANGUAGES:
        body = {k: lang[k] for k in
                ("code", "name", "nativeName", "ttsLang", "accentColor", "sortOrder")}
        res = client.post("/languages", json=body)
        if res.status_code in (201, 409):
            print(f"[3/4] Ngon ngu {lang['name']}: "
                  f"{'tao moi' if res.status_code == 201 else 'da co'}")
        else:
            sys.exit(f"LOI tao ngon ngu {lang['code']}: {res.status_code} {res.text}")

    # 4. Import CSVs
    for lang in LANGUAGES:
        path = SEED_DIR / lang["csv"]
        if not path.exists():
            sys.exit(f"LOI: khong thay {path}")
        with open(path, "rb") as f:
            res = client.post("/imports/study-items",
                              files={"file": (lang["csv"], f, "text/csv")})
        if res.status_code != 201:
            sys.exit(f"LOI import {lang['csv']}: {res.status_code} {res.text}")
        batch = res.json()
        print(f"[4/4] Import {lang['name']}: {batch['importedRows']}/{batch['totalRows']} items"
              + (f" ({batch['failedRows']} loi)" if batch["failedRows"] else ""))
        if batch.get("errorSummary"):
            print("       Loi dau tien:", batch["errorSummary"].splitlines()[0])

    # Summary
    res = client.get("/dashboard/languages")
    print("\n=== HOAN TAT ===")
    for lang in res.json():
        print(f"  {lang['name']}: due {lang['dueCount']} - new {lang['newCount']}")
    print(f"\nDang nhap app bang:\n  Email:    {EMAIL}\n  Mat khau: {PASSWORD}")


if __name__ == "__main__":
    main()
