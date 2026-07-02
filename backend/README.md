# Vocab API — Backend

FastAPI + PostgreSQL backend cho app học từ vựng. Xem `../PLAN.md` và spec gốc.

## Chạy local

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env    # sửa JWT_SECRET, DATABASE_URL

# Tạo migration đầu tiên từ models rồi apply (cần PostgreSQL đang chạy)
alembic revision --autogenerate -m "initial schema"
alembic upgrade head

uvicorn app.main:app --reload
# Swagger: http://localhost:8000/api/docs (khi DEBUG=true)
```

## Test

```bash
pytest        # 20 tests — chạy trên SQLite in-memory, không cần PostgreSQL
```

## Deploy (VPS)

```bash
cp .env.example .env   # điền secrets thật
docker compose up -d --build
docker compose exec api alembic upgrade head
```

## Trạng thái: HOÀN CHỈNH theo acceptance criteria spec §19

| Module | Trạng thái |
|---|---|
| Auth: register, login, refresh **rotation + reuse detection**, logout, me | ✅ |
| Models 11 bảng + indexes (chạy cả SQLite test lẫn PostgreSQL) | ✅ |
| Languages + Language Settings CRUD (validate ratios, soft delete) | ✅ |
| Study Items CRUD (filter, search, pagination, archive) | ✅ |
| Study engine: daily/extra session, candidate rules §9.2, ratio §9.4, ordering §9.5 | ✅ |
| Review PASS/FAIL/SKIP (§8) — transaction, **idempotent**, interval clamp | ✅ |
| Hard items: list + HARD_ITEMS session | ✅ |
| Dashboard: summary (streak, pass rate), languages, history | ✅ |
| Import CSV (mapping §14) + export CSV + backup JSON | ✅ |
| User settings (timezone, TTS) | ✅ |
| Rate limiting (login 5/min, register 3/min, refresh 10/min, import 5/h) | ✅ |
| Test suite: auth flow, algorithm, isolation, import — **20/20 pass** | ✅ |

## API chính

```text
POST /api/auth/register|login|refresh|logout    GET /api/auth/me
GET|POST|PATCH|DELETE /api/languages[/{id}]     GET|PATCH /api/languages/{id}/settings
GET|POST|PATCH|DELETE /api/study-items[/{id}]
POST /api/languages/{id}/study-sessions/daily|extra
GET  /api/languages/{id}/study-sessions/current
GET  /api/study-sessions/{id}                   POST /api/study-sessions/{id}/complete
POST /api/study-sessions/{id}/items/{itemId}/review
GET  /api/hard-items                            POST /api/hard-items/study-sessions
GET  /api/dashboard/summary|languages|history?range=30d
POST /api/imports/study-items                   GET /api/imports/{batchId}
GET  /api/exports/study-items.csv               GET /api/exports/backup.json
GET|PATCH /api/user-settings
```

## Nguyên tắc bảo mật (đã áp dụng toàn bộ)

- Mọi query lọc `user_id = current_user.id`; resource không thuộc user → **404** (không lộ tồn tại).
- Login sai trả thông báo chung — không phân biệt email tồn tại hay không.
- Refresh token: chỉ lưu SHA-256 hash, rotation mỗi lần dùng, reuse → thu hồi cả family.
- Review submission: 1 transaction, idempotent qua `applied_at`.
- "Hôm nay" luôn tính theo `user_settings.timezone`, không theo giờ server.
