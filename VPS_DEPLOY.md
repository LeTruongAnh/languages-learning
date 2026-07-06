# Hướng dẫn DEPLOY VPS (backend + web app)

Điều kiện: đã chạy ổn ở local (xem **LOCAL_GUIDE.md**), code đã đẩy lên GitHub (repo private, kèm `tts.tgz` + `vocab.sql.gz` nếu muốn tái dùng audio/dữ liệu).
VPS: Ubuntu 24.04. Hai kịch bản đều được hướng dẫn: **máy riêng** (Caddy, mục 1.5) và **máy dùng chung đã có nginx** (mục 1.5d — trường hợp VPS 1GB hiện tại).

---

## PHẦN 1 — DEPLOY BACKEND

### 1.1 Chuẩn bị VPS + domain

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
- Trỏ DNS: bản ghi `A` của `merlinle.com` → IP VPS (Caddy cần domain để tự cấp TLS).
- Nếu chọn VPS 1GB, tạo swap trước: `fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile` (+ ghi vào /etc/fstab).

### 1.2 Cài đặt ban đầu (SSH vào VPS, chạy 1 lần)

```bash
# User riêng + firewall
adduser deploy && usermod -aG sudo deploy
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable

# Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy
```

Đăng nhập lại bằng user `deploy`.

### 1.3 Đưa code lên VPS

Cách đơn giản nhất từ máy Windows — nén trước để KHÔNG kéo theo `.venv`/`__pycache__`/`uploads` (nặng hàng trăm MB):

```powershell
cd C:\WORKSPACE\languages-leaning\code
tar --exclude=backend/.venv --exclude=backend/uploads --exclude=backend/__pycache__ `
    --exclude=backend/.pytest_cache -czf backend.tgz backend
scp backend.tgz deploy@<IP-VPS>:~
ssh deploy@<IP-VPS> "tar xzf backend.tgz && mv backend vocab-backend && rm backend.tgz"
```

**Cách B (khuyến nghị) — git clone qua Deploy Key** (repo private):

```bash
# VPS: tạo khóa chỉ-đọc cho repo
ssh-keygen -t ed25519 -C "vps-vocab" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```

GitHub → repo → Settings → **Deploy keys** → Add deploy key → dán khóa, KHÔNG tick write access.

```bash
git clone git@github.com:LeTruongAnh/languages-learning.git ~/languages-learning
cd ~/languages-learning/backend        # backend nằm trong repo; tts.tgz + vocab.sql.gz ở gốc ~/languages-learning/
tar xzf ../tts.tgz -C .   # giải audio -> backend/uploads/
```

Các mục sau dùng đường dẫn `~/languages-learning/backend` thay cho `~/languages-learning/backend`. Restore DB: `gunzip -c ../vocab.sql.gz | docker compose exec -T db psql -U vocab vocab_app` (mục 1.5c). Cập nhật phiên bản: `cd ~/languages-learning && git pull && cd backend && docker compose up -d --build api`.

### 1.4 Cấu hình production

```bash
cd ~/languages-learning/backend
cp .env.example .env
nano .env
```

```env
APP_ENV=production
DEBUG=false                  # QUAN TRỌNG: tắt Swagger ở production
DATABASE_URL=postgresql+asyncpg://vocab:<MẬT-KHẨU-MẠNH>@db:5432/vocab_app
POSTGRES_PASSWORD=<MẬT-KHẨU-MẠNH>       # trùng với password trong DATABASE_URL
JWT_SECRET=<sinh mới: python3 -c "import secrets; print(secrets.token_urlsafe(64))">
ADMIN_EMAILS=thanhphongnguyen3005@gmail.com   # tài khoản quản kho từ vựng
CORS_ORIGINS=                # để trống nếu chưa có web companion
```

Lưu ý `DATABASE_URL` dùng host **`db`** (tên service trong docker-compose), không phải localhost.

Sửa `Caddyfile`: thay `merlinle.com` bằng domain thật.

### 1.5 Khởi chạy

```bash
cd ~/languages-learning/backend

# Thư mục audio TTS: container chạy user không-root nên host dir phải ghi được
mkdir -p uploads/tts && chmod -R 777 uploads

docker compose up -d --build
docker compose exec api alembic upgrade head   # repo đã kèm sẵn migration đầy đủ — KHÔNG chạy autogenerate trên VPS
```

### 1.5b Seed dữ liệu + sinh audio (một lần)

```bash
# Tạo tài khoản + import 9.511 từ/câu (script + CSV đã đóng gói trong image)
docker compose exec api python scripts/seed.py

# Sinh sẵn toàn bộ mp3 phát âm (~30-60 phút; bỏ qua được — từ chưa có audio sẽ sinh lúc bấm loa)
docker compose exec -d api python scripts/generate_tts.py   # -d = chạy nền
docker compose exec api sh -c 'ls uploads/tts | wc -l'      # theo dõi tiến độ
```

Muốn đổi tài khoản seed: `docker compose exec -e SEED_EMAIL=ban@mail.com -e SEED_PASSWORD='MatKhau!' api python scripts/seed.py`

### 1.5c CÁCH NHANH HƠN: mang DB + audio từ máy dev lên (thay cho 1.5b)

Audio mp3 đặt tên theo **UUID của item**, mà seed lại trên VPS sẽ sinh UUID mới → audio cũ không khớp. Muốn tái dùng ~9.5k mp3 đã build ở local thì chuyển cả database lẫn audio, **bỏ hẳn bước `alembic upgrade` + seed**:

```powershell
# Máy dev — nén NGAY TRONG container (Windows không có gzip, và pipe của
# PowerShell làm hỏng dữ liệu nhị phân):
docker exec vocab-pg sh -c "pg_dump -U vocab vocab_app | gzip > /tmp/vocab.sql.gz"
docker cp vocab-pg:/tmp/vocab.sql.gz .
docker exec vocab-pg rm /tmp/vocab.sql.gz
tar -czf tts.tgz -C C:\WORKSPACE\languages-leaning\code\backend uploads
scp vocab.sql.gz tts.tgz deploy@<IP-VPS>:~/languages-learning/backend/
```

```bash
# VPS (db phải còn TRỐNG — dump đã chứa schema + alembic_version):
cd ~/languages-learning/backend
gunzip -c vocab.sql.gz | docker compose exec -T db psql -U vocab vocab_app
tar xzf tts.tgz && chmod -R 777 uploads
docker compose restart api
```

Tài khoản + tiến độ học đi theo dump — đăng nhập y như ở local. Lỡ chạy `alembic upgrade head` trước khi restore → conflict: `docker compose down -v` (xóa volume) rồi `up -d` làm lại. Từ nào thiếu mp3 vẫn tự sinh khi bấm loa.

### 1.5d VPS DÙNG CHUNG đã có nginx (trường hợp máy 1GB RAM, nginx chiếm cổng 80)

Không dùng Caddy — nginx có sẵn làm reverse proxy. Repo đã kèm `docker-compose.override.yml` (tự merge): api chỉ mở `127.0.0.1:8000`, PostgreSQL giảm RAM cho máy 1GB, log giới hạn 30MB/service.

```bash
cd ~/languages-learning/backend
docker compose up -d --build api db     # CHỈ 2 service này, KHÔNG khởi động caddy
```

Thêm site nginx (dùng subdomain, ví dụ `merlinle.com` — trỏ bản ghi A về IP VPS trước):

```bash
sudo tee /etc/nginx/sites-available/vocab << 'NGINX'
server {
    listen 80;
    server_name merlinle.com;
    client_max_body_size 20m;

    # Web app (Flutter web build — file tĩnh, xem §2.2)
    root /var/www/languages-learning;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX
sudo mkdir -p /var/www/languages-learning
sudo ln -s /etc/nginx/sites-available/vocab /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# TLS miễn phí (tự gia hạn):
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d merlinle.com
```

Giữ đĩa sạch trên máy 11GB (còn ~4.7GB): backup giữ 7 bản thay vì 14 (sửa `tail -n +15` thành `tail -n +8` trong cron §1.7), và mỗi tháng chạy `docker system prune -f`.

API base URL cho app mobile: `https://merlinle.com/api`.

### 1.6 Kiểm tra

```bash
docker compose ps                          # 3 service: api, db, caddy đều Up
curl https://merlinle.com/api/health     # {"status":"ok"}
docker compose logs -f api                 # xem log khi cần
```

Test từ ngoài: đăng ký + đăng nhập qua `https://merlinle.com/api/auth/...` như LOCAL_GUIDE.md mục 1.8.

### 1.7 Backup database (bắt buộc)

```bash
mkdir -p ~/backups
crontab -e
```

Thêm dòng (backup 2h sáng mỗi ngày, giữ 14 bản):

```cron
0 2 * * * docker compose -f /home/deploy/vocab-backend/docker-compose.yml exec -T db pg_dump -U vocab vocab_app | gzip > /home/deploy/backups/vocab_$(date +\%F).sql.gz && ls -t /home/deploy/backups/*.gz | tail -n +15 | xargs -r rm
```

Khôi phục: `gunzip -c backup.sql.gz | docker compose exec -T db psql -U vocab vocab_app`

### 1.7b NÂNG CẤP LÊN KIẾN TRÚC CATALOG (một lần, 07/2026)

Bản refactor tách "kho từ dùng chung" khỏi "tiến độ per-user". Nâng cấp DB đang chạy KHÔNG mất dữ liệu (backup trước cho chắc: mục 1.7):

```bash
cd ~/languages-learning && git pull && cd backend
# thêm dòng này vào .env:  ADMIN_EMAILS=thanhphongnguyen3005@gmail.com
docker compose exec -T db psql -U vocab vocab_app < scripts/migrate_to_catalog.sql
docker compose up -d --build api
docker compose exec api alembic stamp head   # đồng bộ mốc migration
curl http://127.0.0.1:8000/api/health
```

Sau nâng cấp: user mới đăng ký thấy ngay toàn bộ kho từ (tiến độ riêng từ 0), audio dùng chung không sinh lại, chỉ admin sửa được kho từ. KHÔNG chạy `alembic revision --autogenerate` trên VPS.

### 1.8 Cập nhật phiên bản mới

```bash
cd ~/languages-learning/backend
# scp/git pull code mới lên, rồi:
docker compose up -d --build api
docker compose exec api alembic upgrade head   # nếu có migration mới
```

### 1.9 Checklist bảo mật trước khi mở cho người dùng

- [ ] `DEBUG=false` (Swagger tắt)
- [ ] `JWT_SECRET` và `POSTGRES_PASSWORD` sinh ngẫu nhiên, khác giá trị dev
- [ ] `.env` không commit vào git
- [ ] `curl http://<IP>:8000` từ ngoài KHÔNG vào được (chỉ Caddy expose 80/443; api chỉ `expose` nội bộ)
- [ ] `https://` hoạt động, HTTP tự redirect (Caddy làm sẵn)
- [ ] Cron backup đã chạy thử 1 lần thành công

---

### 1.10 Cloudflare (tùy chọn, khuyến nghị): che IP VPS + CDN

Thứ tự quan trọng — cấp SSL Let's Encrypt TRƯỚC khi bật proxy:

1. dash.cloudflare.com → Add a domain → plan Free → giữ 2 bản ghi A (`@` và `www` → IP VPS) ở chế độ **DNS only (xám)**.
2. Đổi nameserver tại nơi mua domain sang 2 NS Cloudflare đưa → chờ Active.
3. Trên VPS: `certbot --nginx -d domain -d www.domain` (verify trực tiếp khi chưa proxy).
4. Bật **Proxied (cam)** cho cả 2 bản ghi; **SSL/TLS → Full (strict)** (Flexible sẽ gây redirect loop); bật **Always Use HTTPS**.
5. Kiểm tra: `nslookup domain` trả IP Cloudflare (IP VPS đã ẩn); web + `/api/health` chạy qua HTTPS.

Certbot vẫn tự gia hạn qua proxy. Audio TTS không bị CDN cache nhầm (URL không có đuôi .mp3, kèm token). Khi có nhiều user cần IP thật trong log/rate-limit: cài nginx real-IP module với dải IP Cloudflare.

## PHẦN 2 — BUILD & PHÂN PHỐI APP (Android / Web / iOS)

### 2.1 Android — build APK release

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
flutter build apk --release --dart-define=API_BASE_URL=https://merlinle.com/api

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

### 2.2 Web app — build trên máy dev, upload lên VPS

**KHÔNG build Flutter trên VPS** (SDK ~2GB, build ngốn 2-4GB RAM). Làm trên Windows:

```powershell
cd C:\WORKSPACE\languages-leaning\code\mobile
flutter build web --release --dart-define=API_BASE_URL=https://merlinle.com/api
# Kết quả: mobile\build\web\ (index.html + main.dart.js + assets...)
```

Đưa lên VPS — chọn 1 trong 2:

```powershell
# Cách A — commit vào repo (giống tts.tgz; repo phải Private):
cd C:\WORKSPACE\languages-leaning\code
tar -czf web.tgz -C mobile\build\web .
git add web.tgz && git commit -m "web app build" && git push
# VPS: cd ~/languages-learning && git pull && sudo tar xzf web.tgz -C /var/www/languages-learning

# Cách B — scp trực tiếp:
tar -czf web.tgz -C mobile\build\web .
scp web.tgz deploy@<IP-VPS>:~
# VPS: sudo tar xzf ~/web.tgz -C /var/www/languages-learning && rm ~/web.tgz
```

**Sau MỖI lần deploy web mới:** Cloudflare cache file `.js` ở edge và Flutter web còn có service worker — nên (1) Cloudflare dashboard → Caching → **Purge Everything**; (2) trình duyệt F12 → Application → Service workers → Unregister rồi mở lại tab. Không làm sẽ thấy "vẫn như cũ". Kiểm tra bản trên đĩa đã mới: `grep -c <tên-field-mới> /var/www/<web-root>/main.dart.js`.

Mở `https://merlinle.com` là vào app. Web cùng domain với API nên không cần cấu hình CORS. Web app thêm ~50MB disk, gần như không tốn RAM/CPU (file tĩnh) — cấu hình VPS tối thiểu không đổi so với chạy backend đơn thuần. Lưu ý web không có notification nhắc học (đã ghi trong README mobile); cập nhật phiên bản = build lại + upload đè.

### 2.3 iOS (khi cần)

- Cần macOS + Xcode + Apple Developer account ($99/năm).
- `flutter build ipa --release --dart-define=API_BASE_URL=https://merlinle.com/api`
- Phân phối nhóm nhỏ qua **TestFlight** (tối đa 100 internal tester).

### 2.4 Kiểm tra bản release

1. Cài APK release lên máy thật (không cắm USB debug).
2. Đăng nhập bằng tài khoản trên server production.
3. Chạy checklist LOCAL_GUIDE.md mục 2.4. Phát âm là mp3 từ server (edge-tts) nên KHÔNG phụ thuộc TTS engine của máy — chỉ cần mạng tới server.

---


---

## PHẦN 3 — XỬ LÝ SỰ CỐ TRÊN VPS

| Triệu chứng | Nguyên nhân / cách xử lý |
|---|---|
| `docker compose up` lỗi database | `POSTGRES_PASSWORD` trong `.env` không khớp `DATABASE_URL`; hoặc volume cũ giữ password cũ → `docker volume rm vocab-backend_pgdata` (mất data!) |
| Caddy không cấp được TLS | DNS chưa trỏ đúng IP, hoặc cổng 80/443 bị firewall chặn |
| Loa không kêu trên VPS / 503 khi bấm loa | Container không ghi được `uploads/` (quyền) → `chmod -R 777 uploads` rồi `docker compose restart api`; hoặc VPS không ra được internet (edge-tts cần) |
| API qua domain trả 404 nhưng `docker compose exec api curl localhost:8000/api/health` chạy | Caddyfile dùng `handle_path` (strip mất prefix `/api`) — phải dùng `handle /api/*` như file trong repo |

Sự cố khi dev local: xem LOCAL_GUIDE.md phần 3.
