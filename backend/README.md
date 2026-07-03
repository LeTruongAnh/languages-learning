# Vocab API — Backend

FastAPI + PostgreSQL backend cho app học từ vựng. Xem `../PLAN.md`, `../LOCAL_GUIDE.md` (chạy local) và `../VPS_DEPLOY.md` (deploy).

## Chạy local (tóm tắt — chi tiết trong LOCAL_GUIDE.md)

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate    # Windows
pip install -e ".[dev]"
cp .env.example .env                                # sửa JWT_SECRET, DATABASE_URL

.\scripts\reset_and_seed.ps1     # reset DB + schema + seed 9.511 từ/câu + tài khoản test
python scripts\generate_tts.py    # sinh sẵn audio phát âm (một lần, ~30-60 phút)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Swagger: http://localhost:8000/api/docs (khi DEBUG=true)
```

## Test

```bash
pytest        # 37 tests — SQLite in-memory, không cần PostgreSQL
```

## Trạng thái: HOÀN CHỈNH (vượt acceptance criteria spec §19)

| Module | Trạng thái |
|---|---|
| Auth: register, login, refresh **rotation + reuse detection**, logout, me | ✅ |
| Models 11 bảng + indexes (timestamptz, chạy cả SQLite test lẫn PostgreSQL) | ✅ |
| Languages + Settings CRUD (validate ratios, soft delete, facets cho filter UI) | ✅ |
| Study Items CRUD (filter, search, pagination, archive) | ✅ |
| Study engine: daily/extra/**weekly** session, candidate rules §9.2, sort random/**priority**/oldest | ✅ |
| **SRS v2**: 4 mức AGAIN/HARD/GOOD/EASY + ease factor (SM-2 rút gọn), interval nhân theo ease | ✅ |
| **Undo** thẻ vừa chấm (1 bước kiểu Anki, khôi phục từ review_log snapshot) | ✅ |
| Review submission: 1 transaction, **idempotent** qua applied_at | ✅ |
| Hard items: list + HARD_ITEMS session | ✅ |
| Dashboard: summary (streak **có grace 1 ngày**, pass rate), languages, history | ✅ |
| **TTS server**: mp3 edge-tts neural, cache uploads/tts, sinh on-demand, `?token=` cho audio element | ✅ |
| Import CSV (mapping §14) + export CSV + backup JSON | ✅ |
| User settings (timezone, TTS, nhắc học) + Language settings (direction, weekly, filters, intervals) | ✅ |
| Rate limiting (login 5/min, register 3/min, refresh 10/min, import 5/h) | ✅ |
| **Due forecast** (`dueTomorrow` trong /dashboard/languages) | ✅ |
| **Completion stats**: streak + kỷ lục + thẻ tốt nghiệp (trả về khi complete) | ✅ |
| **Resume phiên dở**: dashboard trả `activeSessionType`, app mở lại đúng phiên khi Tạm dừng | ✅ |
| Test suite **37/37 pass** | ✅ |

## API chính

```text
POST /api/auth/register|login|refresh|logout      GET /api/auth/me
GET|POST|PATCH|DELETE /api/languages[/{id}]       GET|PATCH /api/languages/{id}/settings
GET  /api/languages/{id}/facets                   (distinct difficulty/topic/frequency/situation)
GET|POST|PATCH|DELETE /api/study-items[/{id}]
POST /api/languages/{id}/study-sessions/daily|extra|weekly
GET  /api/languages/{id}/study-sessions/current   GET /api/study-sessions/{id}
POST /api/study-sessions/{id}/items/{itemId}/review    (AGAIN|HARD|GOOD|EASY|SKIP)
POST /api/study-sessions/{id}/items/{itemId}/undo      (chỉ thẻ vừa chấm gần nhất)
POST /api/study-sessions/{id}/complete
GET  /api/hard-items                              POST /api/hard-items/study-sessions
GET  /api/dashboard/summary|languages|history?range=30d
GET  /api/tts/{itemId}                            (mp3; Bearer hoặc ?token=)
POST /api/imports/study-items                     GET /api/imports/{batchId}
GET  /api/exports/study-items.csv                 GET /api/exports/backup.json
GET|PATCH /api/user-settings
```

## Scripts

| Script | Công dụng |
|---|---|
| `scripts/reset_and_seed.ps1` | Reset DB + schema mới nhất + seed toàn bộ dữ liệu (một lệnh) |
| `scripts/seed.py` | Seed tài khoản + languages + import CSV (tự bỏ qua nếu đã có data) |
| `scripts/generate_tts.py` | Sinh mp3 phát âm cho toàn bộ items (edge-tts, chạy lại được) |

## Nguyên tắc bảo mật (đã áp dụng toàn bộ)

- Mọi query lọc `user_id = current_user.id`; resource không thuộc user → **404**.
- Login sai trả thông báo chung — không lộ email tồn tại.
- Refresh token: chỉ lưu SHA-256 hash, rotation, reuse → thu hồi cả family.
- "Hôm nay" luôn tính theo `user_settings.timezone`.

## Lưu ý vận hành trên Windows

Khi sửa code mà hành vi server không đổi: nghi phạm số một là **process cũ giữ cổng 8000** —
uvicorn mới không bind được và chết im lặng, process cũ tiếp tục phục vụ. Restart sạch:

```powershell
Get-Process python* | Stop-Process -Force
netstat -ano | findstr :8000          # phải trống
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
python -B -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
