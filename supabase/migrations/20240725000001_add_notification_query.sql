-- 알림 쿼리 필드 추가
-- 2024-07-25

-- notification_query 필드 추가 (사용자가 설정한 알림 쿼리)
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS notification_query TEXT DEFAULT '최신 과학 뉴스';

-- 인덱스 추가 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_profiles_notification_query 
ON profiles(notification_query);

-- 댓글 추가
COMMENT ON COLUMN profiles.notification_query IS '사용자가 설정한 알림 쿼리 (예: "생명공학 뉴스", "AI 기술 뉴스" 등)'; 