const { createClient } = require('@supabase/supabase-js')

// Supabase 연결 정보
const supabaseUrl = 'https://gtlxkigxfmlslvapgofz.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd0bHhraWd4Zm1sc2x2YXBnb2Z6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgyNDI5NTMsImV4cCI6MjA2MzgxODk1M30.bxL7mOvUkCXf3ns3sHw7_LBbuqd418kkpcqBJ99qudA'

const supabase = createClient(supabaseUrl, supabaseKey)

async function addNotificationQueryColumn() {
  try {
    console.log('🔧 notification_query 컬럼 추가 중...')
    
    // SQL 실행을 위한 rpc 호출
    const { data, error } = await supabase.rpc('exec_sql', {
      sql_query: `
        ALTER TABLE profiles 
        ADD COLUMN IF NOT EXISTS notification_query TEXT DEFAULT '최신 과학 뉴스';
      `
    })
    
    if (error) {
      console.log('❌ SQL 실행 오류:', error)
      
      // 대안: 직접 테이블에 컬럼이 있는지 확인
      console.log('🔍 현재 profiles 테이블 구조 확인 중...')
      const { data: profileData, error: profileError } = await supabase
        .from('profiles')
        .select('*')
        .limit(1)
      
      if (profileError) {
        console.log('❌ profiles 테이블 접근 오류:', profileError)
        return
      }
      
      console.log('📋 profiles 테이블 컬럼들:', Object.keys(profileData[0] || {}))
      
      if ('notification_query' in (profileData[0] || {})) {
        console.log('✅ notification_query 컬럼이 이미 존재합니다!')
      } else {
        console.log('❌ notification_query 컬럼이 없습니다.')
        console.log('\n💡 해결 방법:')
        console.log('1. Supabase 대시보드에서 SQL Editor 열기')
        console.log('2. 다음 SQL 실행:')
        console.log(`
          ALTER TABLE profiles 
          ADD COLUMN IF NOT EXISTS notification_query TEXT DEFAULT '최신 과학 뉴스';
          
          CREATE INDEX IF NOT EXISTS idx_profiles_notification_query 
          ON profiles(notification_query);
          
          COMMENT ON COLUMN profiles.notification_query IS '사용자가 설정한 알림 쿼리 (예: "생명공학 뉴스", "AI 기술 뉴스" 등)';
        `)
      }
    } else {
      console.log('✅ notification_query 컬럼이 성공적으로 추가되었습니다!')
    }
    
  } catch (err) {
    console.log('❌ 예상치 못한 오류:', err)
  }
}

// 스크립트 실행
addNotificationQueryColumn() 