# Kế hoạch triển khai — Mobile Vocabulary Learning App

Nguồn: `mobile_vocab_app_technical_spec_final.md` (v1.0)
Stack đã chốt: **Flutter + FastAPI + PostgreSQL + Docker Compose**

> **TRẠNG THÁI (02/07/2026): MVP HOÀN THÀNH**
> - ✅ Phase 1 — Backend foundation (auth, languages, settings, study items)
> - ✅ Phase 2 — Study engine (sessions, review, hard items, dashboard) — 20/20 test pass
> - ✅ Phase 3 — Mobile Flutter nối API thật (auth guard, study flow, TTS, dashboard, settings)
> - ✅ Phase 4 (backend) — Import CSV, export CSV/JSON backup
> - 🔲 Phase 4 (web companion React/Vite) + Phase 5 (offline queue, charts, notifications) — bước tiếp theo
>
> Chi tiết: `backend/README.md`, `mobile/README.md`

---

## 1. Phân tích spec

### 1.1 Điểm mạnh của spec
- Schema PostgreSQL đầy đủ, generic theo ngôn ngữ (không tách bảng theo từng ngôn ngữ) → thêm ngôn ngữ mới không cần migration.
- Thuật toán review (PASS/FAIL/SKIP, hard level, intervals) định nghĩa rõ, dễ viết unit test.
- Đã có yêu cầu transaction + idempotency cho review submission — tránh double-apply.
- Scope MVP hợp lý: online-first, không offline queue, không mixed session.

### 1.2 Lỗ hổng cần bổ sung (spec chưa nói rõ)

| # | Vấn đề | Quyết định trong kế hoạch |
|---|---|---|
| 1 | Refresh token chỉ nói "refresh token", chưa nói lưu/thu hồi thế nào | Thêm bảng `refresh_tokens` (hash token, expires, revoked) + **rotation**: mỗi lần refresh cấp token mới, thu hồi token cũ. Phát hiện reuse → thu hồi cả chuỗi |
| 2 | Rate limit chỉ nhắc login | Rate limit cả `/auth/register`, `/auth/refresh`, import endpoints (slowapi) |
| 3 | Chưa có password policy | Tối thiểu 8 ký tự; kiểm tra bằng Pydantic validator |
| 4 | `review_intervals[times_review]` có thể out-of-range khi `times_limit > len(intervals)` | Clamp về interval cuối cùng |
| 5 | Timezone: `study_date` phụ thuộc timezone user | Mọi tính toán "today" dùng `user_settings.timezone`, không dùng server time |
| 6 | Session cũ chưa complete từ hôm trước | Job/logic đánh dấu `EXPIRED` khi tạo session ngày mới |
| 7 | Idempotency phía client (mất mạng khi submit) | Response review trả state hiện tại nếu `applied_at` đã set → client retry an toàn |
| 8 | Chưa nói CORS, security headers | CORS whitelist domain web; Caddy thêm HSTS, X-Content-Type-Options |
| 9 | Token lưu ở mobile | `flutter_secure_storage` (Keychain/Keystore), không lưu SharedPreferences |
| 10 | Import file: chưa giới hạn kích thước | Giới hạn 5MB, validate MIME, parse trong background task |

### 1.3 Rủi ro chính
- **TTS chất lượng**: `flutter_tts` dùng voice hệ điều hành — trên Android máy cũ giọng zh-CN có thể kém. Chấp nhận cho MVP, phase sau cân nhắc cloud TTS.
- **Session generation đúng ratio** là phần logic phức tạp nhất → viết test trước (candidate rules, new/review ratio, fill fallback, ordering).

---

## 2. Kiến trúc tổng thể

```text
┌─────────────┐     HTTPS/JSON      ┌──────────────────────────┐
│ Flutter app │ ──────────────────► │ Caddy (TLS, headers)     │
│  (Riverpod) │                     │   /api/* → FastAPI :8000 │
└─────────────┘                     │   /*     → web static    │
                                    └──────────┬───────────────┘
                                               │ SQLAlchemy async
                                    ┌──────────▼───────────────┐
                                    │ PostgreSQL 16            │
                                    └──────────────────────────┘
```

Backend layering (spec §12): `routes → services → repositories → models`. Business logic chỉ nằm ở services; routes chỉ validate + gọi service.

---

## 3. Thiết kế bảo mật (backend)

### 3.1 Authentication
- **Access token**: JWT HS256, TTL 15 phút, claims: `sub` (user_id), `exp`, `iat`, `jti`.
- **Refresh token**: random 256-bit, TTL 30 ngày, lưu **SHA-256 hash** trong bảng `refresh_tokens`, rotation mỗi lần dùng, phát hiện reuse → revoke toàn bộ token của user.
- **Password**: Argon2id (`argon2-cffi`), tham số mặc định RFC 9106 low-memory (phù hợp VPS 4GB).
- **Login rate limit**: 5 lần/phút/IP + 10 lần/giờ/email. Trả 429, không tiết lộ email tồn tại hay không (thông báo lỗi chung "invalid credentials").

### 3.2 Authorization — user-scoped mọi truy vấn
- Dependency `get_current_user` decode JWT → mọi repository nhận `user_id` bắt buộc (tham số vị trí đầu, không optional).
- Resource lồng nhau (session item, language settings) phải verify chuỗi sở hữu: `session.user_id == current_user.id` trước khi đụng session_items.
- Trả **404** (không phải 403) khi resource không thuộc user → không leak sự tồn tại.

### 3.3 Input & transport
- Pydantic schemas validate toàn bộ input (ratios tổng = 1, daily_limit 1–200, result ∈ {PASS,FAIL,SKIP}...).
- SQLAlchemy parameterized — không raw SQL string.
- CORS: chỉ whitelist domain web companion; mobile không cần CORS.
- Caddy: tự động TLS, thêm `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`.
- Secrets qua env (`.env` không commit); JWT secret ≥ 256-bit random.

### 3.4 Phía mobile
- Token trong `flutter_secure_storage`.
- Interceptor Dio: tự gắn access token, tự refresh khi 401 (single-flight để tránh refresh đua nhau), logout khi refresh fail.
- Không log token/response body ở release build.

---

## 4. Thiết kế UI/UX mobile

### 4.1 Design system

| Token | Giá trị |
|---|---|
| Nền | `#F7F8FA` (light), surface trắng, radius 16 |
| Chữ chính | `#1A1D26`; phụ `#6B7280` |
| Accent Chinese | `#E0533D` (warm rose) |
| Accent English | `#2563EB` (blue) |
| Hard Items | `#F59E0B` (orange) |
| Review | `#8B5CF6` (purple) |
| PASS | `#16A34A` · FAIL `#DC2626` · SKIP `#9CA3AF` |
| Font | Inter/system; chữ học chính 40–48px bold; pinyin 20px |
| Tap target | tối thiểu 48×48dp; nút PASS/FAIL/SKIP cao 56dp, cố định đáy màn hình |

### 4.2 Điều hướng
Bottom nav 3 tab MVP: **Home · Dashboard · Settings**. Study mở từ language card (full-screen, không tab bar) — đúng spec §5.3.

### 4.3 Nguyên tắc màn hình Study (màn quan trọng nhất)
- 1 hành động chính/màn: card ở giữa, 3 nút kết quả cố định đáy → học 1 tay, không nhìn tìm nút.
- Progress bar mỏng trên đầu + `5/20`; badge loại item (Vocabulary/Sentence, New/Review) màu theo hệ.
- Nghĩa tiếng Việt ẩn mặc định, tap "Show meaning" — đúng flow active recall.
- TTS: nút loa cạnh từ, auto-speak theo settings; haptic nhẹ khi bấm PASS/FAIL.
- FAIL bên trái, PASS bên phải (thuận ngón cái phải), SKIP nhỏ ở giữa — giảm bấm nhầm.

### 4.4 Danh sách màn hình (spec §11.4)
Login → Home → LanguageStudy (transition) → StudyCard → SessionComplete; Dashboard; Settings; HardItems; ItemList/ItemForm (phase 4).

Mockup HTML tương tác: xem `design/mobile_mockup.html`.

---

## 5. Lộ trình triển khai

### Phase 1 — Backend Foundation (tuần 1–2)
Setup FastAPI + SQLAlchemy async + Alembic; migration đủ 9 bảng + `refresh_tokens`; auth đầy đủ (register, login, refresh rotation, logout, me); CRUD languages, language_settings, study_items; rate limiting; pytest + CI cơ bản.
**Done khi**: auth flow chạy, user A không đọc được data user B (có test chứng minh).

### Phase 2 — Study Engine (tuần 3–4)
Candidate selection (đủ 9 rule §9.2); daily/extra session; review submission (transaction + idempotent); review logs; hard items session; dashboard summary/languages/history.
**Done khi**: acceptance criteria backend §19 pass toàn bộ, coverage logic review 100%.

### Phase 3 — Mobile MVP (tuần 5–7)
Flutter + Riverpod + go_router + Dio; Login; Home language cards; Study flow đầy đủ + TTS; SessionComplete; Dashboard; Settings.
**Done khi**: acceptance criteria mobile §19 pass trên cả Android + iOS.

### Phase 4 — Import & Web companion (tuần 8–9)
CSV/XLSX import (migrate từ Google Sheets theo mapping §14); export; React/Vite web quản lý items.

### Phase 5 — Polish
Offline queue, charts, notifications, weekly review.

---

## 6. Cấu trúc thư mục dự án

```text
code/
├── PLAN.md
├── mobile_vocab_app_technical_spec_final.md
├── design/
│   └── mobile_mockup.html        ← mockup tương tác các màn hình
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/       (config, security, database, errors, rate_limit)
│   │   ├── models/     (user, refresh_token, language, ..., import_batch)
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── api/routes/
│   ├── alembic/
│   ├── tests/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── Caddyfile
│   └── .env.example
└── mobile/
    └── lib/
        ├── main.dart
        ├── app/        (router, theme)
        ├── core/       (api, auth, storage, errors)
        └── features/   (auth, home, study, dashboard, settings, hard_items)
```

---

## 7. Kiểm thử & chất lượng

- **Backend**: pytest + httpx AsyncClient; test bắt buộc: review algorithm (PASS/FAIL/SKIP mọi nhánh), session generation ratios, idempotency, cross-user isolation, refresh rotation + reuse detection.
- **Mobile**: unit test cho state notifiers; widget test StudyCard; golden test theme.
- **Định nghĩa hoàn thành mỗi phase** = acceptance criteria §19 tương ứng + test xanh.


---

## 8. Roadmap cải tiến (học từ các app khác — 02/07/2026)

Nguồn tham chiếu pattern: Anki (SRS thuần), Duolingo (gamification/habit), Memrise (đa dạng bài tập), Pimsleur (audio-first), Clozemaster (cloze), Pleco (tra cứu tiếng Trung).

### Ưu tiên cao — ✅ ĐÃ TRIỂN KHAI (02/07/2026): undo, 4 mức trả lời, ease factor SM-2, chiều học đảo, nhắc học + streak grace 1 ngày
| # | Cải tiến | Học từ | Ghi chú triển khai |
|---|---|---|---|
| 1 | **Undo thẻ vừa trả lời** | Anki | Bấm nhầm PASS/FAIL rất phổ biến. Backend: endpoint revert dùng old_* trong review_logs (chỉ cho thẻ gần nhất, trong phiên đang mở) |
| 2 | **4 mức trả lời: Quên / Khó / Nhớ / Dễ** thay PASS/FAIL | Anki | Interval scale theo mức: Khó ×0.7, Dễ ×1.5. Giữ SKIP. Schema: last_result mở rộng |
| 3 | **Ease factor per item (SM-2 rút gọn)** | Anki | Thay interval cố định [1,3,7] bằng interval × ease; ease tăng/giảm theo kết quả. Cột mới: ease numeric default 2.5 |
| 4 | **Chiều học đảo**: Việt→từ, nghe TTS→đoán từ | Anki, Pimsleur | Setting per language: direction mix. Card hiện nghĩa trước, giấu từ |
| 5 | **Push notification nhắc học + bảo vệ streak** | Duolingo | Phase 5 đã có kế hoạch; local notification là đủ cho MVP |

### Ưu tiên vừa — ✅ 02/07/2026: đã thêm Settings nâng cao (bộ lọc, SRS knobs, sort priority) + Weekly review từ config sheet cũ
| # | Cải tiến | Học từ | Ghi chú |
|---|---|---|---|
| 6 | Trắc nghiệm 4 đáp án xen kẽ flashcard | Duolingo, Memrise | Sinh 3 đáp án nhiễu từ items cùng topic/difficulty — không cần AI |
| 7 | Cloze câu ví dụ (đục lỗ từ đang học trong example) | Clozemaster | Dữ liệu example sẵn có, chỉ cần render + input |
| 8 | Heatmap lịch học (kiểu GitHub) trong Dashboard | Anki | Đã có API /dashboard/history — chỉ cần UI |
| 9 | Thêm/sửa từ ngay trong app (ItemForm) | Pleco | Spec đã có ItemFormScreen — Phase 4 |
| 10 | Âm báo đúng/sai nhẹ + haptic mạnh hơn khi FAIL | Duolingo | package audioplayers, file âm ngắn |

### Cân nhắc sau (chi phí cao / cần cân nhắc)
- **Gõ lại từ (typing test)** — Memrise: hiệu quả cao nhưng gõ tiếng Trung cần IME, trải nghiệm mobile kém → chỉ làm cho English trước.
- **Leaderboard/XP** — Duolingo: với 1–10 người dùng thân quen có thể vui, nhưng dễ thành áp lực; để rất sau.
- **AI sinh câu ví dụ mới** — tránh theo spec §16 (không host model trên VPS nhỏ); nếu làm thì gọi API ngoài, sinh offline khi import.

Nguyên tắc chọn: app này là công cụ SRS cá nhân — ưu tiên các cải tiến làm **thuật toán nhớ tốt hơn** (1–4) trước các cải tiến làm **app vui hơn** (5–10).
