#!/usr/bin/env python3
"""
Supabase에 직접 연결해서 notification_query 컬럼을 추가하는 스크립트
"""

import psycopg2
import os
from urllib.parse import urlparse

# Supabase 연결 정보
SUPABASE_URL = "https://gtlxkigxfmlslvapgofz.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd0bHhraWd4Zm1sc2x2YXBnb2Z6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgyNDI5NTMsImV4cCI6MjA2MzgxODk1M30.bxL7mOvUkCXf3ns3sHw7_LBbuqd418kkpcqBJ99qudA"

# Supabase URL에서 호스트 정보 추출
parsed_url = urlparse(SUPABASE_URL)
host = parsed_url.hostname

# PostgreSQL 연결 정보 (Supabase는 PostgreSQL 기반)
# 실제 연결 정보는 Supabase 대시보드에서 확인해야 합니다
# 여기서는 일반적인 Supabase PostgreSQL 연결 패턴을 사용합니다

def add_notification_query_column():
    """notification_query 컬럼을 profiles 테이블에 추가"""
    
    # Supabase PostgreSQL 연결 정보
    # 실제 값들은 Supabase 대시보드 > Settings > Database에서 확인
    db_host = "db.gtlxkigxfmlslvapgofz.supabase.co"
    db_name = "postgres"
    db_user = "postgres"
    db_password = "your-db-password"  # 실제 비밀번호 필요
    
    try:
        # PostgreSQL 연결
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=5432
        )
        
        cursor = conn.cursor()
        
        # notification_query 컬럼 추가
        sql = """
        ALTER TABLE profiles 
        ADD COLUMN IF NOT EXISTS notification_query TEXT DEFAULT '최신 과학 뉴스';
        """
        
        print("notification_query 컬럼 추가 중...")
        cursor.execute(sql)
        
        # 인덱스 추가
        index_sql = """
        CREATE INDEX IF NOT EXISTS idx_profiles_notification_query 
        ON profiles(notification_query);
        """
        
        print("인덱스 추가 중...")
        cursor.execute(index_sql)
        
        # 댓글 추가
        comment_sql = """
        COMMENT ON COLUMN profiles.notification_query IS '사용자가 설정한 알림 쿼리 (예: "생명공학 뉴스", "AI 기술 뉴스" 등)';
        """
        
        print("컬럼 댓글 추가 중...")
        cursor.execute(comment_sql)
        
        # 변경사항 커밋
        conn.commit()
        
        print("✅ notification_query 컬럼이 성공적으로 추가되었습니다!")
        
        # 컬럼이 제대로 추가되었는지 확인
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'profiles' AND column_name = 'notification_query';")
        result = cursor.fetchone()
        
        if result:
            print("✅ 컬럼 확인 완료: notification_query 컬럼이 존재합니다.")
        else:
            print("❌ 컬럼 확인 실패: notification_query 컬럼을 찾을 수 없습니다.")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("\n💡 해결 방법:")
        print("1. Supabase 대시보드에서 Database > Connection string 확인")
        print("2. 실제 데이터베이스 비밀번호 입력")
        print("3. 또는 Supabase CLI를 사용하여 마이그레이션 실행")
        
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    print("🔧 Supabase profiles 테이블에 notification_query 컬럼 추가")
    print("=" * 60)
    add_notification_query_column() 