-- =============================================================
-- MIGRATION: per-user items  ->  shared catalog + user_item_progress
-- Chạy 1 lần trên DB đang có dữ liệu (local hoặc VPS):
--   docker compose exec -T db psql -U vocab vocab_app < scripts/migrate_to_catalog.sql
-- Giữ nguyên: toàn bộ nội dung từ/câu, tiến độ học của admin, audio TTS
-- (item UUID không đổi). CẢNH BÁO: các tài khoản KHÁC admin sẽ bị xóa
-- (chỉ là account test không dữ liệu).
-- =============================================================
BEGIN;

-- 0) Admin = tài khoản chính (SỬA EMAIL NẾU KHÁC)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
UPDATE users SET is_admin = TRUE WHERE email = 'thanhphongnguyen3005@gmail.com';

-- 1) Xóa account phụ (cascade sạch dữ liệu rác của họ)
DELETE FROM users WHERE is_admin = FALSE;

-- 2) Bảng tiến độ per-user
CREATE TABLE IF NOT EXISTS user_item_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES study_items(id) ON DELETE CASCADE,
    times_review INTEGER NOT NULL DEFAULT 0,
    passed BOOLEAN NOT NULL DEFAULT FALSE,
    wrong_count INTEGER NOT NULL DEFAULT 0,
    last_result VARCHAR(20),
    last_date_review DATE,
    next_review_date DATE,
    ease NUMERIC(4,2) NOT NULL DEFAULT 2.50,
    interval_days INTEGER NOT NULL DEFAULT 0,
    hard_level VARCHAR(30) NOT NULL DEFAULT 'Normal',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, item_id)
);
CREATE INDEX IF NOT EXISTS idx_progress_due  ON user_item_progress (user_id, next_review_date, passed);
CREATE INDEX IF NOT EXISTS idx_progress_hard ON user_item_progress (user_id, hard_level);
CREATE INDEX IF NOT EXISTS ix_user_item_progress_user_id ON user_item_progress (user_id);
CREATE INDEX IF NOT EXISTS ix_user_item_progress_item_id ON user_item_progress (item_id);

-- 3) Chuyển tiến độ đã học sang bảng mới (lazy: chỉ thẻ đã từng đụng tới)
INSERT INTO user_item_progress (user_id, item_id, times_review, passed, wrong_count,
    last_result, last_date_review, next_review_date, ease, interval_days, hard_level)
SELECT user_id, id, times_review, passed, wrong_count,
    last_result, last_date_review, next_review_date, ease, interval_days, hard_level
FROM study_items
WHERE times_review > 0 OR passed OR wrong_count > 0
   OR last_date_review IS NOT NULL OR next_review_date IS NOT NULL;

-- 4) study_items -> catalog thuần nội dung
ALTER TABLE study_items
  DROP COLUMN IF EXISTS user_id,
  DROP COLUMN IF EXISTS last_date_review,
  DROP COLUMN IF EXISTS next_review_date,
  DROP COLUMN IF EXISTS times_review,
  DROP COLUMN IF EXISTS passed,
  DROP COLUMN IF EXISTS wrong_count,
  DROP COLUMN IF EXISTS last_result,
  DROP COLUMN IF EXISTS hard_level,
  DROP COLUMN IF EXISTS ease,
  DROP COLUMN IF EXISTS interval_days,
  DROP COLUMN IF EXISTS image_path;
CREATE INDEX IF NOT EXISTS idx_study_items_language ON study_items (language_id);
CREATE INDEX IF NOT EXISTS idx_study_items_type     ON study_items (language_id, item_type);
CREATE INDEX IF NOT EXISTS idx_study_items_archived ON study_items (is_archived);

-- 5) languages -> global catalog
ALTER TABLE languages DROP COLUMN IF EXISTS user_id;
ALTER TABLE languages ADD CONSTRAINT languages_code_key UNIQUE (code);

COMMIT;

-- Kiểm tra nhanh sau khi chạy:
--   SELECT count(*) FROM study_items;            -- ~9511 (nguyên vẹn)
--   SELECT count(*) FROM user_item_progress;     -- = số thẻ đã học
--   SELECT email, is_admin FROM users;
