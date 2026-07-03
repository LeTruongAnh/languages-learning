# Hướng dẫn chạy LOCAL (dev & test)

Áp dụng cho máy dev Windows: **backend/** (FastAPI + PostgreSQL trong Docker) và **mobile/** (Flutter chạy Chrome / emulator / điện thoại thật cùng Wi-Fi).
Deploy lên server: xem **VPS_DEPLOY.md**.

---

## PHẦN 1 — TEST LOCAL: BACKEND

### 1.1 Yêu cầu

- Python 3.12+ (`python --version`)
- Docker Desktop (để chạy PostgreSQL local)

### 1.2 Cài đặt

```powershell
cd C:\WORKSPACE\languages-leaning\code\backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

### 1.3 Chạy unit test (không cần database)

Test suite chạy trên SQLite in-memory:

```powershell
pytest
# Kỳ vọng: 36 passed
```

Đây là bước kiểm tra nhanh nhất — nếu 36/36 pass thì logic auth, study engine, isolation đều đúng.

### 1.4 Chạy PostgreSQL local

```powershell
docker run -d --name vocab-pg -p 5432:5432 `
  -e POSTGRES_DB=vocab_app -e POSTGRES_USER=vocab -e POSTGRES_PASSWORD=devpass `
  -v vocab_pgdata:/var/lib/postgresql/data postgres:16-alpine
```

### 1.5 Cấu hình `.env`

```powershell
copy .env.example .env
```

Sửa `.env`:

```env
APP_ENV=development
DEBUG=true
DATABASE_URL=postgresql+asyncpg://vocab:devpass@localhost:5432/vocab_app
JWT_SECRET=<chạy lệnh dưới để sinh>
```

Sinh JWT secret:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 1.6 Tạo schema + seed dữ liệu (một lệnh)

Cách nhanh nhất — reset sạch DB, tạo schema mới nhất và import 9.511 từ/câu mẫu:

```powershell
.\scripts\reset_and_seed.ps1
```

Script tự đọc cổng/mật khẩu từ `.env`, tự chờ PostgreSQL, tự chạy API tạm nếu server chưa bật. Dùng lại bất cứ khi nào muốn làm sạch dữ liệu (sau khi đổi schema, seed hỏng...).

**Nâng schema KHÔNG mất dữ liệu** (khi có cột mới, ví dụ ảnh minh họa `image_path`):

```powershell
alembic revision --autogenerate -m "schema change"
alembic upgrade head
```

**Sinh audio phát âm (một lần, sau seed):** app phát mp3 sinh sẵn bằng giọng neural (edge-tts) thay vì TTS của thiết bị. Chạy:

```powershell
pip install -e ".[dev]"          # cài edge-tts (dependency mới)
python scripts\generate_tts.py   # ~30-60 phút cho 9.5k items, chạy lại được nếu đứt
```

Không bắt buộc — từ nào chưa có audio sẽ được sinh tự động lần đầu bấm loa (trễ ~1 giây). Sinh sẵn để phát tức thì.

Cách thủ công (chỉ tạo schema, không seed):

```powershell
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### 1.7 Chạy server

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Mở Swagger UI: **http://localhost:8000/api/docs** (có vì `DEBUG=true`).

### 1.8 Smoke test bằng curl (luồng đầy đủ)

```bash
# 1. Đăng ký + đăng nhập
curl -s -X POST http://localhost:8000/api/auth/register -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"matkhau123","displayName":"Phong"}'

TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"matkhau123"}' | python -c "import sys,json;print(json.load(sys.stdin)['accessToken'])")
AUTH="Authorization: Bearer $TOKEN"

# 2. Tạo ngôn ngữ Chinese
LANG_ID=$(curl -s -X POST http://localhost:8000/api/languages -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"code":"zh","name":"Chinese","ttsLang":"zh-CN","accentColor":"#E0533D"}' | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

# 3. Thêm từ vựng
curl -s -X POST http://localhost:8000/api/study-items -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"languageId\":\"$LANG_ID\",\"itemType\":\"VOCABULARY\",\"text\":\"你好\",\"pronunciation\":\"nǐ hǎo\",\"vietnameseMeaning\":\"Xin chào\"}"

# 4. Tạo phiên học hôm nay
curl -s -X POST http://localhost:8000/api/languages/$LANG_ID/study-sessions/daily -H "$AUTH"
# -> lấy session id + items[0].id từ response, rồi submit review:
# curl -X POST http://localhost:8000/api/study-sessions/{sessionId}/items/{sessionItemId}/review \
#   -H "$AUTH" -H "Content-Type: application/json" -d '{"result":"PASS"}'

# 5. Dashboard
curl -s http://localhost:8000/api/dashboard/summary -H "$AUTH"
```

Trên Windows PowerShell, dùng Swagger UI sẽ dễ hơn — bấm **Authorize**, dán access token, test từng endpoint.

### 1.9 Import dữ liệu từ Google Sheets

Xuất Google Sheets ra CSV theo cột spec §14 (`language,item_type,text,pronunciation,vietnamese_meaning,...`), rồi upload qua Swagger `POST /api/imports/study-items` hoặc:

```bash
curl -X POST http://localhost:8000/api/imports/study-items -H "$AUTH" -F "file=@vocab.csv"
```

---

## PHẦN 2 — TEST LOCAL: MOBILE

### 2.1 Yêu cầu

- Flutter SDK 3.22+ (`flutter doctor` không lỗi đỏ)
- Android Studio + emulator, hoặc điện thoại thật bật USB debugging

### 2.2 Khởi tạo (chạy 1 lần)

```powershell
cd C:\WORKSPACE\languages-leaning\code\mobile
flutter create . --platforms=android,ios --org com.phong.vocab
flutter pub get
```

### 2.3 Chạy app — chọn đúng base URL

| Môi trường | Lệnh |
|---|---|
| Android emulator | `flutter run` (mặc định `http://10.0.2.2:8000/api` → localhost máy dev) |
| iOS simulator | `flutter run --dart-define=API_BASE_URL=http://localhost:8000/api` |
| Điện thoại thật (cùng Wi-Fi) | `flutter run --dart-define=API_BASE_URL=http://<IP-máy-dev>:8000/api` |
| Chrome (Flutter web) | `flutter create . --platforms=web` (1 lần) rồi `flutter run -d chrome --web-port 5555 --dart-define=API_BASE_URL=http://localhost:8000/api` — backend cần `CORS_ORIGINS=http://localhost:5555` trong `.env` |

Lấy IP máy dev: `ipconfig` → IPv4 Address. Backend phải chạy với `--host 0.0.0.0` và Windows Firewall cho phép cổng 8000.

**Lưu ý Android**: HTTP (không HTTPS) trên thiết bị thật cần bật cleartext. Thêm vào `android/app/src/main/AndroidManifest.xml` trong thẻ `<application>`:

```xml
android:usesCleartextTraffic="true"
```

(Chỉ dùng khi dev — bản production dùng HTTPS nên xóa dòng này.)

### 2.4 Checklist test luồng chính

1. Đăng ký tài khoản mới trong app → tự đăng nhập vào Home.
2. Home hiển thị language card (cần tạo ngôn ngữ + item trước qua Swagger/import — mục 1.8, 1.9).
3. Bấm **Bắt đầu học** → thẻ hiện ra, tự phát âm (mp3 từ server).
4. Bấm **Hiện nghĩa** → chấm Quên/Khó/Nhớ/Dễ (hoặc Bỏ qua) → thẻ tiếp theo; thử nút ↩ hoàn tác.
5. Học hết → màn Hoàn thành hiện 🔥 streak / 🏆 kỷ lục / 🎓 thẻ tốt nghiệp → Về Home → progress + forecast cập nhật.
6. Tắt app mở lại → vẫn đăng nhập (token trong secure storage), phiên dở dang resume đúng thẻ.
7. Dashboard hiển thị số liệu; Settings đổi tốc độ đọc có hiệu lực; Đăng xuất → về Login.
8. Tắt backend → app hiện "Không kết nối được máy chủ" + nút Thử lại (không crash).

---


---

## PHẦN 3 — XỬ LÝ SỰ CỐ KHI CHẠY LOCAL

| Triệu chứng | Nguyên nhân / cách xử lý |
|---|---|
| App báo "Không kết nối được máy chủ" trên emulator | Backend chưa chạy `--host 0.0.0.0`, hoặc sai base URL (emulator phải dùng `10.0.2.2`) |
| Thiết bị thật không gọi được API dev | Khác Wi-Fi, hoặc Windows Firewall chặn cổng 8000, hoặc thiếu `usesCleartextTraffic` |
| 401 liên tục sau một thời gian | Refresh token hết hạn (30 ngày) → đăng nhập lại là đúng thiết kế |
| `alembic` báo `InvalidPasswordError` khi dev local | (1) PostgreSQL native Windows đang chiếm cổng 5432 → đổi Docker sang `-p 5433:5432` + sửa `.env`; (2) password `.env` khác lệnh `docker run`; (3) volume cũ giữ password cũ → `docker volume rm vocab_pgdata` rồi tạo lại |
| Alembic autogenerate ra `drop_column('image_path')` trên máy dev | Cột thừa từ tính năng ảnh đã gỡ — cứ apply (không mất dữ liệu) hoặc xóa tay: `ALTER TABLE study_items DROP COLUMN IF EXISTS image_path;` |
| Session hôm qua vẫn hiện | Đúng thiết kế: session cũ tự chuyển EXPIRED khi tạo session ngày mới |
| Sửa code backend nhưng hành vi không đổi / route mới không xuất hiện | Process python cũ giữ cổng 8000, uvicorn mới chết im lặng. Restart sạch: `Get-Process python* \| Stop-Process -Force` → `netstat -ano \| findstr :8000` phải trống → xóa `__pycache__` → chạy lại |
| Loa báo lỗi "Format error" trên web | Server trả JSON lỗi thay vì mp3 — xem console Flutter dòng `TTS prefetch failed: HTTP ...` để biết nguyên nhân thật (503 = thiếu edge-tts / lỗi mạng; 404 = server chạy code cũ) |
