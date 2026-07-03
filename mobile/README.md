# Vocab App — Flutter

App mobile học từ vựng, đã nối API thật. Xem `../PLAN.md`, mockup UI: `../design/mobile_mockup.html`.

## Setup

```bash
cd mobile
flutter create . --platforms=android,ios --org com.phong.vocab   # sinh android/ ios/ (chạy 1 lần)
flutter pub get

# Android emulator (backend chạy trên máy host cổng 8000):
flutter run

# Thiết bị thật / production:
flutter run --dart-define=API_BASE_URL=https://yourdomain.com/api
```

Base URL mặc định `http://10.0.2.2:8000/api` (Android emulator → localhost máy host). iOS simulator dùng `--dart-define=API_BASE_URL=http://localhost:8000/api`.

## Trạng thái: Phase 3 HOÀN CHỈNH — đã nối API thật

| Phần | Trạng thái |
|---|---|
| Auth: login/register/logout, bootstrap từ secure storage, auth guard router | ✅ |
| Dio interceptor: tự gắn token, tự refresh khi 401 (single-flight), logout khi hết hạn | ✅ |
| Home: language cards từ `/dashboard/languages` + streak, pull-to-refresh | ✅ |
| Study flow: daily/extra/hard session, PASS/FAIL/SKIP, resume giữa chừng, retry khi mất mạng | ✅ |
| Phát âm: mp3 server (edge-tts neural) — đồng nhất mọi thiết bị, loa hoạt động cả hard session | ✅ |
| Completion view: thống kê Pass/Fail/Skip cuối phiên | ✅ |
| Dashboard: stat cards + breakdown ngôn ngữ | ✅ |
| Settings: TTS toggles + speech rate (PATCH API), logout, múi giờ | ✅ |
| Hard Items: danh sách + tạo HARD_ITEMS session | ✅ |
| SRS v2: 4 mức Quên/Khó/Nhớ/Dễ + ease factor | ✅ |
| Undo thẻ vừa chấm (1 bước, kiểu Anki) | ✅ |
| Chiều học: Từ→Nghĩa / Nghĩa→Từ / Nghe→Từ / Trộn (per language) | ✅ |
| Nhắc học hằng ngày (local notification, không hỗ trợ web) | ✅ |
| Settings nâng cao per language: bộ lọc difficulty/topic/frequency/situation, times limit, intervals, reset on fail, include passed, sort mode | ✅ |
| Ôn tập tuần: chọn ngày + số thẻ, nút hiện trên Home đúng ngày, ưu tiên thẻ sai nhiều | ✅ |
| Nút chấm chỉ hiện sau khi lật đáp án (chuẩn Anki), nút Hiện nghĩa full-width | ✅ |
| Layout desktop web: nội dung giới hạn 520px, không loãng | ✅ |
| Tạm dừng giữa bài → Home hiện "Tiếp tục học (đang dở)" mở lại đúng phiên cũ (daily/extra/weekly) | ✅ |
| Due forecast trên Home: đến hạn hôm nay · mới · dồn sang mai | ✅ |
| Completion screen: 🔥 streak, 🏆 kỷ lục mới, 🎓 thẻ tốt nghiệp | ✅ |

## Cấu trúc

```text
lib/
  main.dart                 ProviderScope + MaterialApp.router
  app/
    router.dart             go_router + auth guard (redirect theo AuthStatus)
    theme.dart              Design tokens (khớp mockup HTML)
  core/
    api/endpoints.dart      API_BASE_URL (dart-define)
    api/api_client.dart     Dio + auto-refresh token
    models/models.dart      DTOs parse JSON camelCase
    providers.dart          tokenStorage / apiClient / tts providers
    storage/token_storage.dart   flutter_secure_storage
    tts/tts_service.dart    flutter_tts
  features/
    auth/      data/auth_repository + presentation/auth_controller, login_screen
    home/      data/home_repository + presentation/home_screen
    study/     data/study_repository + presentation/study_controller, study_screen
    dashboard/ presentation/dashboard_screen
    settings/  data/settings_repository + presentation/settings_screen
    hard_items/presentation/hard_items_screen
```

## Ghi chú

- Hard Items session trộn nhiều ngôn ngữ nên tắt auto-TTS (không xác định voice); nút loa ẩn.
- Quản lý item + cài đặt ngôn ngữ chi tiết (ratios, intervals) làm qua web companion/API — ngoài scope mobile MVP theo spec §4.3.
- Phase tiếp theo (spec Phase 5): offline queue, charts, notifications.
