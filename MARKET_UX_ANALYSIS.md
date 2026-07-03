# Nghiên cứu thị trường & Phân tích UX app hiện tại

*Cập nhật: 07/2026 — tài liệu phân tích, chưa triển khai code.*

---

## 1. Bức tranh thị trường

Thị trường app học ngôn ngữ đạt ~6,7 tỷ USD năm 2026, tăng trưởng ~15%/năm. Toàn bộ thị trường chia thành hai trường phái rõ rệt, và app của bạn cần biết mình đứng ở đâu giữa hai cực này.

**Trường phái "hiệu quả ghi nhớ"** (Anki, Clozemaster, Pleco, Lingvist): tối ưu thuật toán SRS, dữ liệu do người học tự kiểm soát, giao diện tối giản. Điểm mạnh là kết quả học thật; điểm chết là UX — Anki bị chê gần như đồng loạt vì onboarding kém, người mới phải "học cách dùng app trước khi học từ". Hệ quả kinh doanh: Anki doanh thu <5 triệu USD/năm dù phương pháp vượt trội, trong khi Duolingo hơn 1 tỷ USD.

**Trường phái "hiệu quả giữ chân"** (Duolingo, Memrise, Quizlet): tối ưu thói quen — streak, quest, XP, leaderboard. Số liệu đáng chú ý từ Duolingo: người có streak 7+ ngày quay lại app **gấp 2,4 lần** người không có; **streak freeze** giúp streak trung bình dài hơn 48%; **Daily Quests** khi ra mắt tăng 25% DAU; churn tháng giảm từ 47% (2020) xuống 28% (2023) chủ yếu nhờ kiến trúc streak + notification. Điểm yếu: hiệu quả học thật bị nghi ngờ — học xong Duolingo/HelloChinese thường dừng ở ~HSK 3-4 rồi "kẹt cao nguyên trung cấp".

**Ba xu hướng kỹ thuật đang định hình 2025-2026:**

1. **FSRS thay SM-2.** Anki đã đổi mặc định sang FSRS từ bản 23.10. Benchmark trên 500 triệu lượt review cho thấy FSRS cần **ít hơn 20-30% lượt ôn** cho cùng mức ghi nhớ (lưu ý: số liệu từ mô phỏng, chưa phải thử nghiệm đối chứng). SM-2 vẫn dùng tốt nhưng đang thành "thế hệ cũ".
2. **Học từ trong ngữ cảnh câu** (sentence mining). Clozemaster xây cả sản phẩm quanh nguyên tắc "từ học trong câu nhớ lâu hơn và dùng tự nhiên hơn từ học cô lập" — đúng hướng app của bạn đã đi (có cả câu lẫn từ).
3. **AI hội thoại** (Duolingo Video Call với AI) — ngoài scope hiện tại, ghi nhận để biết.

**Thị trường Việt Nam:** người học VN phổ biến dùng Quizlet, Anki, Duolingo cho tiếng Anh; Pleco (từ điển), Anki, HSK Online/SuperTest cho tiếng Trung. Tức là người dùng mục tiêu (chính bạn) đã quen mô hình flashcard + SRS — app không cần "gamify hoá" kiểu Duolingo để hấp dẫn, nhưng nên vay mượn có chọn lọc các cơ chế giữ thói quen.

---

## 2. App hiện tại đứng ở đâu

Định vị thực tế: **"Anki cá nhân hoá cho một người dùng nghiêm túc"** — dữ liệu riêng (9.511 từ/câu từ Google Sheets cũ), SRS SM-2 rút gọn có ease factor, 4 mức chấm, undo, 4 chiều học, weekly review, hard items, TTS neural chất lượng cao, nhắc học + streak có grace. Về triết lý, app nằm ở trường phái "hiệu quả ghi nhớ" nhưng đã vá đúng những chỗ Anki yếu nhất về UX (giao diện hiện đại, TTS tự động, cấu hình tập trung).

### Hành vi (behavior) hiện tại của app — mô tả chính xác

**Vòng lặp hằng ngày:** Home hiện card mỗi ngôn ngữ với progress hôm nay → "Bắt đầu học" tạo daily session (idempotent — mỗi ngôn ngữ 1 phiên/ngày theo múi giờ user). Phiên chọn thẻ theo quy tắc: item đến hạn (`next_review ≤ hôm nay`) + item mới, số lượng từ/câu theo setting riêng từng loại, lọc theo difficulty/topic/frequency/situation nếu bật, sắp xếp random / ưu tiên sai nhiều / cũ nhất.

**Trong phiên:** thẻ hiện mặt trước theo chiều học (Từ→Nghĩa / Nghĩa→Từ / Nghe→Từ / Trộn), auto-đọc TTS (trừ chiều Nghĩa→Từ), bấm "Hiện nghĩa" mới thấy 4 nút chấm Quên/Khó/Nhớ/Dễ (chuẩn Anki — tránh chấm trước khi nghĩ). Chấm xong: ease đổi (−0.20/−0.15/0/+0.15, kẹp 1.30-3.00), interval nhân theo ease, Quên thì reset (nếu bật reset_on_fail). Undo được 1 bước. Đến `times_limit` lần Nhớ thì thẻ "tốt nghiệp". Có back/forward xem lại thẻ, kết thúc bài giữa chừng, resume phiên dở.

**Giữ thói quen:** streak tính theo ngày có review, có grace 1 ngày (tương đương streak freeze tự động, miễn phí — hào phóng hơn Duolingo). Nhắc học 1 notification/ngày giờ cố định (không hỗ trợ web).

**Dữ liệu vào/ra:** import CSV, export CSV + backup JSON. Thêm/sửa từng từ: chỉ qua API/Swagger, chưa có UI.

---

## 3. Ưu điểm — đối chiếu chuẩn thị trường

| Điểm mạnh | So với thị trường |
|---|---|
| SRS 4 mức + ease + undo + 4 chiều học | Ngang tính năng lõi Anki — vượt Quizlet/Duolingo về chiều sâu SRS |
| Học cả từ lẫn câu có ngữ cảnh, cùng SRS | Đúng xu hướng sentence-mining (Clozemaster); Anki mặc định không có |
| TTS neural server, đồng nhất mọi thiết bị, cache mp3 | Ngang app trả phí; Anki cần addon, Quizlet TTS máy đọc kém hơn |
| Chấm sau khi lật đáp án, nút bố cục chuẩn | Đúng best practice active recall |
| Streak + grace 1 ngày + nhắc học | Có nền tảng của cơ chế giữ chân hiệu quả nhất thị trường (streak 7+ ngày = retention ×2,4) |
| Cấu hình sâu per-language (filter, interval, sort, weekly) | Mức Anki power-user, nhưng UI gọn hơn Anki nhiều |
| Dữ liệu của riêng bạn, self-host, không phí thuê bao | Khác biệt lớn nhất so với mọi app thương mại |
| Bảo mật chuẩn (JWT rotation, Argon2, user-scoped 404) | Vượt yêu cầu của app cá nhân |

## 4. Nhược điểm — theo mức nghiêm trọng

**Nghiêm trọng (chặn người dùng mới, lệch chuẩn thị trường):**

1. **Onboarding trống** — user mới đăng ký xong thấy Home rỗng, không có cách nào thêm dữ liệu trong app (phải import CSV qua Swagger). Đây chính xác là lỗi "Anki syndrome" mà thị trường đã chứng minh giết sản phẩm. Với bạn hiện tại không sao (đã seed), nhưng là nợ UX lớn nhất nếu thêm người dùng.
2. **Không quản lý từ vựng trong app** — không thêm nhanh 1 từ vừa gặp, không sửa nghĩa sai, không archive từ đã thuộc hẳn. Vòng lặp "gặp từ mới → nhập ngay" là core loop của người học nghiêm túc (lý do Pleco/Anki sống khoẻ).

**Trung bình (giảm hiệu quả giữ thói quen):**

3. **Home thiếu "due forecast"** — không biết hôm nay còn bao nhiêu thẻ đến hạn, ngày mai dồn bao nhiêu. Anki/FSRS đều hiển thị; thiếu nó user không cảm được "nợ ôn tập" đang tích.
4. **Nhắc học tĩnh** — 1 notification giờ cố định. Chuẩn thị trường (Duolingo): nhắc động "sắp mất streak X ngày" vào buổi tối *chỉ khi* hôm đó chưa học — loss-aversion mạnh hơn nhiều lần nhắc theo lịch.
5. **Không có phản hồi cảm xúc cuối phiên** — màn Hoàn thành hiện số liệu khô. Không cần confetti kiểu Duolingo, nhưng một dòng "streak 12 ngày 🔥 / kỷ lục mới / +15 từ đã tốt nghiệp" gần như miễn phí về công sức mà đóng đúng habit loop (hành động → phần thưởng).
6. **Phiên trộn từ + câu ngẫu nhiên** — đã phân tích riêng: gây context-switching; phương án khối (từ trước, câu sau) rẻ mà hiệu quả.

**Nhẹ / dài hạn:**

7. **SM-2 rút gọn vs FSRS** — kém hơn ~20-30% hiệu suất ôn theo benchmark, nhưng với <10k thẻ và 1 user, chênh lệch thực tế nhỏ; nâng cấp là việc lớn (FSRS cần 17-21 tham số + optimizer).
8. **Không offline** — mất mạng là không học được; Anki mạnh nhất khoản này. Chấp nhận được với mô hình self-host + dùng chủ yếu ở nhà.
9. **Thống kê nông** — có summary + history nhưng thiếu heatmap ngày học, đường cong ghi nhớ, dự báo workload 7 ngày.
10. **Không có widget/glance** — widget streak của Duolingo được ghi nhận hiệu quả ngang push notification. Chỉ khả thi khi đã build Android.

---

## 5. Đề xuất ưu tiên (chờ duyệt, chưa code)

Nguyên tắc chọn: giữ định vị "công cụ học nghiêm túc", chỉ vay của Duolingo những cơ chế thói quen đã được chứng minh bằng số liệu, bỏ qua gamification trang trí (XP, leaderboard — vô nghĩa với 1 user).

**P1 — đáng làm ngay, công nhỏ lợi lớn:**
- Màn quản lý từ vựng trong app: thêm nhanh / sửa / archive + tìm kiếm (backend API đã có đủ, chỉ thiếu UI).
- Due forecast trên Home: "Hôm nay: 12 đến hạn + 15 mới · Ngày mai: 23".
- Completion screen có cảm xúc: streak, kỷ lục, số thẻ tốt nghiệp trong phiên.

**P2 — công vừa:**
- Nhắc học động: tối chỉ nhắc nếu hôm đó chưa học, nội dung nêu số streak đang giữ.
- Sắp xếp khối từ→câu trong phiên (đã bàn ở phân tích trước, phương án a).
- Onboarding cho user mới: starter deck hoặc luồng import trong app (chỉ cần khi mở cho người khác dùng).

**P3 — dài hạn:**
- Heatmap + dự báo workload trong Dashboard.
- FSRS thay SM-2 (đánh giá lại khi dữ liệu review đủ dày, ~6 tháng sử dụng).
- Offline queue, widget Android — sau khi bản APK dùng ổn định.

---

## Nguồn tham khảo

- [Business of Apps — Language Learning App Market (2026)](https://www.businessofapps.com/data/language-learning-app-market/)
- [Business Research Insights — Language Learning Application Market](https://www.businessresearchinsights.com/market-reports/language-learning-application-market-102456)
- [Deconstructor of Fun — Duolingo streaks: 2x daily retention](https://duolingo.deconstructoroffun.com/mechanics/streaks)
- [Deconstructor of Fun — Duolingo gaming principles & DAU growth](https://www.deconstructoroffun.com/blog/2025/4/14/duolingo-how-the-15b-app-uses-gaming-principles-to-supercharge-dau-growth)
- [Trophy — Duolingo Gamification Case Study (2026)](https://trophy.so/blog/duolingo-gamification-case-study)
- [Digia — Duolingo habit-forming reminders UX breakdown](https://www.digia.tech/post/duolingo-habit-forming-reminders-retention-architecture/)
- [Anki FAQ — What algorithm does Anki use (FSRS)](https://faqs.ankiweb.net/what-spaced-repetition-algorithm)
- [MemoForge — FSRS vs SM-2 guide 2025](https://memoforge.app/blog/fsrs-vs-sm2-anki-algorithm-guide-2025/)
- [Neurako — FSRS vs SM-2 compared](https://www.neurako.com/blog/fsrs-vs-sm2-spaced-repetition-algorithms-compared)
- [Tactyqal — Why Anki failed (góc nhìn kinh doanh)](https://tactyqal.com/blog/why-anki-failed-an-entrepreneurs-perspective/)
- [Brainscape — Does Anki work?](https://www.brainscape.com/academy/does-anki-work/)
- [Clozemaster — Sentence mining](https://www.clozemaster.com/blog/sentence-mining/)
- [Clozemaster — Best apps to learn Chinese 2026](https://www.clozemaster.com/blog/best-apps-to-learn-chinese/)
- [Duoplanet — Duolingo widget](https://duoplanet.com/duolingo-widget/)
- [Tân Việt Prime — Top app học tiếng Trung 2025](https://tanvietprime.edu.vn/app-hoc-tieng-trung/)
- [VTCPay — App học từ vựng tiếng Anh 2025](https://vtcpay.vn/blog/app-hoc-tu-vung-tieng-anh-mien-phi.html)
