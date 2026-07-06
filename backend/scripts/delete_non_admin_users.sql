-- Xoa TAT CA user thuong (khong phai admin) + toan bo du lieu lien quan.
-- Cascade tu dong don: refresh_tokens, user_settings, language_settings,
-- user_item_progress, study_sessions (+ session items), review_logs,
-- import_batches. KHO TU VUNG (catalog) va AUDIO khong bi anh huong.
--
-- Xem truoc danh sach se xoa:
--   SELECT email, display_name, created_at FROM users WHERE is_admin = FALSE;
--
-- Chay:
--   Local: docker exec -i vocab-pg psql -U vocab vocab_app < scripts/delete_non_admin_users.sql
--   VPS:   docker compose exec -T db psql -U vocab vocab_app < scripts/delete_non_admin_users.sql

BEGIN;

DELETE FROM users WHERE is_admin = FALSE;

COMMIT;

-- Kiem tra: SELECT email, is_admin FROM users;
