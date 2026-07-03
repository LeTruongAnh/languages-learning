# Hướng dẫn Test Local & Deploy VPS

Áp dụng cho: **backend/** (FastAPI + PostgreSQL) và **mobile/** (Flutter).
Máy dev: Windows. VPS: Ubuntu 24.04, 2 vCPU / 4GB RAM (spec §16).

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

## PHẦN 3 — DEPLOY BACKEND LÊN VPS

### 3.1 Chuẩn bị VPS + domain

**Cấu hình VPS cần thiết** (đo theo stack thật: FastAPI 1 worker + PostgreSQL 16 + Caddy, ~10k items):

| Thành phần | RAM thực dùng |
|---|---|
| PostgreSQL (shared_buffers=256MB, max_connections=30) | ~300-400MB |
| API (uvicorn + edge-tts lúc sinh audio) | ~150-250MB |
| Caddy | ~30-50MB |
| Ubuntu nền | ~250-300MB |

| Mức | Cấu hình | Phù hợp |
|---|---|---|
| Tối thiểu | 1 vCPU / 1GB RAM / 20GB SSD | Chạy được (1-3 user) nhưng sát RAM — bắt buộc thêm 2GB swap, build image sẽ chậm |
| **Khuyến nghị** | **1-2 vCPU / 2GB RAM / 25GB SSD** (~$6-12/tháng) | 1-10 user, dư đầu cho build + backup + TTS batch |
| Thoải mái | 2 vCPU / 4GB RAM / 40GB SSD (spec §16) | Nhiều user hơn / thêm web companion sau này |

Disk thực dùng: image Docker ~350MB + PG data <1GB + audio TTS ~200-300MB (9.5k mp3) → 20GB là đủ rộng. Băng thông không đáng kể (mp3 ~15KB/file, có cache client). VPS cần ra được internet (edge-tts gọi endpoint của Microsoft).

- OS: Ubuntu 24.04.
- Trỏ DNS: bản ghi `A` của `yourdomain.com` → IP VPS (Caddy cần domain để tự cấp TLS).
- Nếu chọn VPS 1GB, tạo swap trước: `fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile` (+ ghi vào /etc/fstab).

### 3.2 Cài đặt ban đầu (SSH vào VPS, chạy 1 lần)

```bash
# User riêng + firewall
adduser deploy && usermod -aG sudo deploy
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable

# Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy
```

Đăng nhập lại bằng user `deploy`.

### 3.3 Đưa code lên VPS

Cách đơn giản nhất từ máy Windows — nén trước để KHÔNG kéo theo `.venv`/`__pycache__`/`uploads` (nặng hàng trăm MB):

```powershell
cd C:\WORKSPACE\languages-leaning\code
tar --exclude=backend/.venv --exclude=backend/uploads --exclude=backend/__pycache__ `
    --exclude=backend/.pytest_cache -czf backend.tgz backend
scp backend.tgz deploy@<IP-VPS>:~
ssh deploy@<IP-VPS> "tar xzf backend.tgz && mv backend vocab-backend && rm backend.tgz"
```

(Về lâu dài nên dùng git repo: `git clone` trên VPS.)

### 3.4 Cấu hình production

```bash
cd ~/vocab-backend
cp .env.example .env
nano .env
```

```env
APP_ENV=production
DEBUG=false                  # QUAN TRỌNG: tắt Swagger ở production
DATABASE_URL=postgresql+asyncpg://vocab:<MẬT-KHẨU-MẠNH>@db:5432/vocab_app
POSTGRES_PASSWORD=<MẬT-KHẨU-MẠNH>       # trùng với password trong DATABASE_URL
JWT_SECRET=<sinh mới: python3 -c "import secrets; print(secrets.token_urlsafe(64))">
CORS_ORIGINS=                # để trống nếu chưa có web companion
```

Lưu ý `DATABASE_URL` dùng host **`db`** (tên service trong docker-compose), không phải localhost.

Sửa `Caddyfile`: thay `yourdomain.com` bằng domain thật.

### 3.5 Khởi chạy

```bash
cd ~/vocab-backend

# Thư mục audio TTS: container chạy user không-root nên host dir phải ghi được
mkdir -p uploads/tts && chmod -R 777 uploads

docker compose up -d --build
docker compose exec api alembic upgrade head   # repo đã kèm sẵn migration đầy đủ — KHÔNG chạy autogenerate trên VPS
```

### 3.5b Seed dữ liệu + sinh audio (một lần)

```bash
# Tạo tài khoản + import 9.511 từ/câu (script + CSV đã đóng gói trong image)
docker compose exec api python scripts/seed.py

# Sinh sẵn toàn bộ mp3 phát âm (~30-60 phút; bỏ qua được — từ chưa có audio sẽ sinh lúc bấm loa)
docker compose exec -d api python scripts/generate_tts.py   # -d = chạy nền
docker compose exec api sh -c 'ls uploads/tts | wc -l'      # theo dõi tiến độ
```

Muốn đổi tài khoản seed: `docker compose exec -e SEED_EMAIL=ban@mail.com -e SEED_PASSWORD='MatKhau!' api python scripts/seed.py`

### 3.5c CÁCH NHANH HƠN: mang DB + audio từ máy dev lên (thay cho 3.5b)

Audio mp3 đặt tên theo **UUID của item**, mà seed lại trên VPS sẽ sinh UUID mới → audio cũ không khớp. Muốn tái dùng ~9.5k mp3 đã build ở local thì chuyển cả database lẫn audio, **bỏ hẳn bước `alembic upgrade` + seed**:

```powershell
# Máy dev — nén NGAY TRONG container (Windows không có gzip, và pipe của
# PowerShell làm hỏng dữ liệu nhị phân):
docker exec vocab-pg sh -c "pg_dump -U vocab vocab_app | gzip > /tmp/vocab.sql.gz"
docker cp vocab-pg:/tmp/vocab.sql.gz .
docker exec vocab-pg rm /tmp/vocab.sql.gz
tar -czf tts.tgz -C C:\WORKSPACE\languages-leaning\code\backend uploads
scp vocab.sql.gz tts.tgz deploy@<IP-VPS>:~/vocab-backend/
```

```bash
# VPS (db phải còn TRỐNG — dump đã chứa schema + alembic_version):
cd ~/vocab-backend
gunzip -c vocab.sql.gz | docker compose exec -T db psql -U vocab vocab_app
tar xzf tts.tgz && chmod -R 777 uploads
docker compose restart api
```

Tài khoản + tiến độ học đi theo dump — đăng nhập y như ở local. Lỡ chạy `alembic upgrade head` trước khi restore → conflict: `docker compose down -v` (xóa volume) rồi `up -d` làm lại. Từ nào thiếu mp3 vẫn tự sinh khi bấm loa.

### 3.6 Kiểm tra

```bash
docker compose ps                          # 3 service: api, db, caddy đều Up
curl https://yourdomain.com/api/health     # {"status":"ok"}
docker compose logs -f api                 # xem log khi cần
```

Test từ ngoài: đăng ký + đăng nhập qua `https://yourdomain.com/api/auth/...` như mục 1.8.

### 3.7 Backup database (bắt buộc)

```bash
mkdir -p ~/backups
crontab -e
```

Thêm dòng (backup 2h sáng mỗi ngày, giữ 14 bản):

```cron
0 2 * * * docker compose -f /home/deploy/vocab-backend/docker-compose.yml exec -T db pg_dump -U vocab vocab_app | gzip > /home/deploy/backups/vocab_$(date +\%F).sql.gz && ls -t /home/deploy/backups/*.gz | tail -n +15 | xargs -r rm
```

Khôi phục: `gunzip -c backup.sql.gz | docker compose exec -T db psql -U vocab vocab_app`

### 3.8 Cập nhật phiên bản mới

```bash
cd ~/vocab-backend
# scp/git pull code mới lên, rồi:
docker compose up -d --build api
docker compose exec api alembic upgrade head   # nếu có migration mới
```

### 3.9 Checklist bảo mật trước khi mở cho người dùng

- [ ] `DEBUG=false` (Swagger tắt)
- [ ] `JWT_SECRET` và `POSTGRES_PASSWORD` sinh ngẫu nhiên, khác giá trị dev
- [ ] `.env` không commit vào git
- [ ] `curl http://<IP>:8000` từ ngoài KHÔNG vào được (chỉ Caddy expose 80/443; api chỉ `expose` nội bộ)
- [ ] `https://` hoạt động, HTTP tự redirect (Caddy làm sẵn)
- [ ] Cron backup đã chạy thử 1 lần thành công

---

## PHẦN 4 — BUILD & PHÂN PHỐI MOBILE APP

### 4.1 Android — build APK release

**Bước 1 — tạo scaffold** (một lần, trong `mobile/`):

```powershell
flutter create . --platforms=android --org com.phong.vocab
```

**Bước 2 — sửa `android\app\src\main\AndroidManifest.xml`:** thêm quyền mạng (release không tự có) và cleartext (khi backend còn HTTP):

```xml
<uses-permission android:name="android.permission.INTERNET"/>
<application android:usesCleartextTraffic="true" ...>
```

Khi đã có VPS HTTPS → xóa dòng `usesCleartextTraffic`.

**Bước 3 — sửa `android\app\build.gradle.kts`:** package thông báo cần desugaring:

```kotlin
android {
    compileOptions {
        isCoreLibraryDesugaringEnabled = true
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}
dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
}
```

(File Groovy `build.gradle` cũ: `coreLibraryDesugaringEnabled true` / `coreLibraryDesugaring 'com.android.tools:desugar_jdk_libs:2.1.4'`.)

**Bước 4 — build** (URL bị nướng cứng vào APK lúc build):

```powershell
# Dev LAN (điện thoại cùng Wi-Fi, backend chạy --host 0.0.0.0, firewall mở 8000):
flutter build apk --release --dart-define=API_BASE_URL=http://<IP-máy-dev>:8000/api

# Production (sau khi deploy VPS):
flutter build apk --release --dart-define=API_BASE_URL=https://yourdomain.com/api

# File nhỏ hơn (~8-10MB, lấy bản arm64):
flutter build apk --release --split-per-abi --dart-define=API_BASE_URL=...
```

Kết quả: `build\app\outputs\flutter-apk\app-release.apk`.

**Bước 5 — cài:** gửi APK qua Zalo/Drive/USB → mở file → cho phép "cài từ nguồn không xác định".

**Chữ ký:** mặc định release ký bằng debug key — đủ cho 1-10 người tự cài. Chỉ cần keystore riêng khi lên Google Play:

```powershell
keytool -genkey -v -keystore c:\keys\vocab-upload.jks -storetype JKS `
  -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

rồi cấu hình signing theo https://docs.flutter.dev/deployment/android#sign-the-app

### 4.2 iOS (khi cần)

- Cần macOS + Xcode + Apple Developer account ($99/năm).
- `flutter build ipa --release --dart-define=API_BASE_URL=https://yourdomain.com/api`
- Phân phối nhóm nhỏ qua **TestFlight** (tối đa 100 internal tester).

### 4.3 Kiểm tra bản release

1. Cài APK release lên máy thật (không cắm USB debug).
2. Đăng nhập bằng tài khoản trên server production.
3. Chạy checklist mục 2.4. Phát âm là mp3 từ server (edge-tts) nên KHÔNG phụ thuộc TTS engine của máy — chỉ cần mạng tới server.

---

## PHẦN 5 — XỬ LÝ SỰ CỐ THƯỜNG GẶP

| Triệu chứng | Nguyên nhân / cách xử lý |
|---|---|
| App báo "Không kết nối được máy chủ" trên emulator | Backend chưa chạy `--host 0.0.0.0`, hoặc sai base URL (emulator phải dùng `10.0.2.2`) |
| Thiết bị thật không gọi được API dev | Khác Wi-Fi, hoặc Windows Firewall chặn cổng 8000, hoặc thiếu `usesCleartextTraffic` |
| 401 liên tục sau một thời gian | Refresh token hết hạn (30 ngày) → đăng nhập lại là đúng thiết kế |
| `alembic` báo `InvalidPasswordError` khi dev local | (1) PostgreSQL native Windows đang chiếm cổng 5432 → đổi Docker sang `-p 5433:5432` + sửa `.env`; (2) password `.env` khác lệnh `docker run`; (3) volume cũ giữ password cũ → `docker volume rm vocab_pgdata` rồi tạo lại |
| `docker compose up` lỗi database | `POSTGRES_PASSWORD` trong `.env` không khớp `DATABASE_URL`; hoặc volume cũ giữ password cũ → `docker volume rm vocab-backend_pgdata` (mất data!) |
| Caddy không cấp được TLS | DNS chưa trỏ đúng IP, hoặc cổng 80/443 bị firewall chặn |
| Loa không kêu trên VPS / 503 khi bấm loa | Container không ghi được `uploads/` (quyền) → `chmod -R 777 uploads` rồi `docker compose restart api`; hoặc VPS không ra được internet (edge-tts cần) |
| API qua domain trả 404 nhưng `docker compose exec api curl localhost:8000/api/health` chạy | Caddyfile dùng `handle_path` (strip mất prefix `/api`) — phải dùng `handle /api/*` như file trong repo |
| Alembic autogenerate ra `drop_column('image_path')` trên máy dev | Cột thừa từ tính năng ảnh đã gỡ — cứ apply (không mất dữ liệu) hoặc xóa tay: `ALTER TABLE study_items DROP COLUMN IF EXISTS image_path;` |
| Session hôm qua vẫn hiện | Đúng thiết kế: session cũ tự chuyển EXPIRED khi tạo session ngày mới |
| Sửa code backend nhưng hành vi không đổi / route mới không xuất hiện | Process python cũ giữ cổng 8000, uvicorn mới chết im lặng. Restart sạch: `Get-Process python* \| Stop-Process -Force` → `netstat -ano \| findstr :8000` phải trống → xóa `__pycache__` → chạy lại |
| Loa báo lỗi "Format error" trên web | Server trả JSON lỗi thay vì mp3 — xem console Flutter dòng `TTS prefetch failed: HTTP ...` để biết nguyên nhân thật (503 = thiếu edge-tts / lỗi mạng; 404 = server chạy code cũ) |
