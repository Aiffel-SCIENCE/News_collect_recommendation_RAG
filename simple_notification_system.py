from supabase import create_client, Client
import schedule
import time
from datetime import datetime
import requests
import os
import sys

# 프로젝트 루트 경로 설정
_current_file_path = os.path.abspath(__file__)
_project_root = os.path.dirname(_current_file_path)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(_project_root, ".env"))

# news_recommendation.py의 함수들 임포트
from src.app.news_recommendation import extract_profile_keywords, extract_keywords_from_query

# 환경 변수에서 API 키 로드
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# API 키 검증
if not BREVO_API_KEY:
    print("⚠️  WARNING: BREVO_API_KEY가 설정되지 않았습니다. 이메일 알림이 비활성화됩니다.")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️  WARNING: Supabase 설정이 완료되지 않았습니다. 데이터베이스 연결이 실패할 수 있습니다.")

# Slack 메시지 전송 함수
def send_slack_message(message: str, webhook_url: str):
    payload = {"text": message}
    response = requests.post(webhook_url, json=payload)
    if response.status_code == 200:
        print(f"✅ Slack 메시지 전송 성공: {webhook_url}")
    else:
        print(f"❌ 전송 실패: {response.status_code}, {response.text}")

# Brevo 이메일 전송 함수
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

def send_brevo_email(to_email, subject, content):
    if not BREVO_API_KEY:
        print("❌ BREVO_API_KEY가 설정되지 않아 이메일을 전송할 수 없습니다.")
        return
        
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        sender={"name": "AIGEN Science", "email": "x9520207@gmail.com"},
        subject=subject,
        text_content=content
    )
    try:
        response = api_instance.send_transac_email(send_smtp_email)
        print("✅ Email sent:", response.message_id)
    except ApiException as e:
        print("❌ Failed to send email:", e)

def generate_personalized_query(profile_context: str) -> str:
    """
    news_recommendation.py의 extract_profile_keywords 함수를 활용하여 개인화된 쿼리 생성
    """
    try:
        # 프로필 컨텍스트에서 키워드 추출
        keywords = extract_profile_keywords(profile_context)
        
        if keywords:
            # 키워드를 조합하여 쿼리 생성
            query = f"{' '.join(keywords)} 뉴스"
            print(f"프로필 기반 쿼리 생성: {query}")
            return query
        else:
            # 키워드 추출 실패 시 기본 쿼리
            return "최신 과학 뉴스"
            
    except Exception as e:
        print(f"개인화 쿼리 생성 중 오류: {e}")
        return "최신 과학 뉴스"

def RAG(profile_context: str, notification_query: str = None):
    """
    사용자 프로필 컨텍스트를 기반으로 개인화된 뉴스 추천 생성
    news_recommendation.py의 기존 함수들을 활용
    """
    try:
        # 사용자가 설정한 쿼리가 있으면 사용, 없으면 profile_context 기반으로 생성
        if notification_query and notification_query.strip() and notification_query != "최신 과학 뉴스":
            query = notification_query
        elif profile_context and len(profile_context.strip()) > 0:
            # 프로필 컨텍스트에서 키워드 추출하여 쿼리 생성
            query = generate_personalized_query(profile_context)
        else:
            # 기본 쿼리
            query = "최신 과학 뉴스"
        
        # 뉴스 추천 API 호출 (환경 변수에서 URL 로드)
        recommendation_url = os.environ.get("NEWS_RECOMMENDATION_API_URL", "http://34.61.170.171:8001/recommendations")
        
        payload = {
            "query": query,
            "profile_context": profile_context,
            "num_recommendations": 3
        }
        
        print(f"쿼리: {query}")
        print(f"프로필 컨텍스트: {profile_context}")
        
        response = requests.post(recommendation_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("recommended_news"):
                news_items = data["recommended_news"][:3]  # 상위 3개만
                recommendations = []
                
                for item in news_items:
                    title = item.get("title", "제목 없음")
                    summary = item.get("summary", "")
                    if summary:
                        recommendations.append(f"📰 {title}: {summary[:100]}...")
                    else:
                        recommendations.append(f"📰 {title}")
                
                if recommendations:
                    return "\n".join(recommendations)
        
        # API 호출 실패 시 기본 메시지
        if profile_context:
            return f"프로필 기반 개인화 뉴스 추천: {profile_context[:100]}..."
        else:
            return "오늘의 주요 과학 뉴스를 확인해보세요!"
            
    except Exception as e:
        print(f"RAG 추천 생성 중 오류: {e}")
        # 오류 발생 시 기본 메시지
        if profile_context:
            return f"프로필 기반 개인화 뉴스 추천: {profile_context[:100]}..."
        else:
            return "오늘의 주요 과학 뉴스를 확인해보세요!"

# Supabase 클라이언트 초기화
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None
    print("⚠️  WARNING: Supabase 클라이언트가 초기화되지 않았습니다.")

def fetch_and_notify():
    if not supabase:
        print("❌ Supabase 클라이언트가 초기화되지 않아 알림을 전송할 수 없습니다.")
        return
        
    try:
        # 실제 profiles 테이블 구조에 맞게 조회
        response = (
            supabase.table("profiles")
            .select("username, bio, slack_webhook_url, email, notification_time, notification_query")
            .execute()
        )
        data = response.data
        user_dict = {}
        now = datetime.now().strftime("%H:%M")
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 알림 전송 시작")
        
        for user in data: # 딕셔너리 형태로 저장하기.
            username = user.get("username")
            profile_context = user.get("bio", "")  # bio를 profile_context로 사용
            slack_webhook_url = user.get("slack_webhook_url")
            email = user.get("email")
            notification_time = user.get("notification_time")
            notification_query = user.get("notification_query", "최신 과학 뉴스")  # profile에서 읽어옴
            user_dict[username] = [profile_context, slack_webhook_url, email, notification_time, notification_query]
            
            # 알림 시간과 현재 시간이 같으면 알림 전송
            if notification_time == now:
                print(f"사용자 {username}에게 알림 전송 중...")
                rag_result = RAG(profile_context, notification_query)  # 쿼리 전달
                message = f"[{username}] {rag_result}"
                
                if slack_webhook_url:
                    send_slack_message(message, webhook_url=slack_webhook_url)
                if email:
                    send_brevo_email(email, "AIGEN Science - 개인화 뉴스 알림", message)
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] username 기준 리스트 딕셔너리:")
        print(f"총 {len(user_dict)}명의 사용자 정보 조회됨")
        for username, info in user_dict.items():
            profile_context, slack_url, email, notification_time, notification_query = info
            print(f"  - {username}: {notification_time} (쿼리: {notification_query}, Slack: {'설정됨' if slack_url else '미설정'}, Email: {'설정됨' if email else '미설정'})")
            
    except Exception as e:
        print(f"알림 전송 중 오류 발생: {e}")
        # 오류 발생 시에도 시스템이 계속 실행되도록 함

# 1시간마다(정각) 실행
schedule.every().hour.at(":00").do(fetch_and_notify)

if __name__ == "__main__":
    print("🚀 AIGEN Science 알림 시스템 시작")
    print("📅 매시간 정각에 알림 전송 예정")
    print("📧 이메일 및 Slack 알림 지원")
    print("=" * 50)
    
    fetch_and_notify()  # 시작 시 1회 실행
    while True:
        schedule.run_pending()
        time.sleep(1) 