#!/usr/bin/env python3
"""
간단한 알림 시스템 테스트 스크립트 (news_recommendation.py 함수 활용)
"""

import sys
import os
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simple_notification_system import RAG, fetch_and_notify, supabase
from src.app.news_recommendation import extract_profile_keywords

def test_profile_keywords():
    """프로필 키워드 추출 테스트"""
    print("🔍 프로필 키워드 추출 테스트")
    print("=" * 50)
    
    test_profiles = [
        "바이오 제약 배고픔 빵 과자 세포",
        "생명공학과 대학원생으로, 암 치료제 개발에 관심이 있습니다.",
        "인공지능 연구원으로, 머신러닝과 딥러닝 분야의 최신 동향을 추적합니다.",
        "물리학자로, 양자컴퓨팅과 양자역학 연구를 하고 있습니다.",
        "화학과 학생입니다.",
        "",  # 빈 프로필 테스트
    ]
    
    for i, profile in enumerate(test_profiles, 1):
        print(f"\n테스트 {i}: {profile[:50]}{'...' if len(profile) > 50 else ''}")
        try:
            keywords = extract_profile_keywords(profile)
            print(f"추출된 키워드: {keywords}")
        except Exception as e:
            print(f"오류: {e}")

def test_rag_function():
    """RAG 함수 테스트"""
    print("\n🧪 RAG 함수 테스트")
    print("=" * 50)
    
    # 실제 사용자 프로필 예시 (제공된 정보 기반)
    test_cases = [
        {
            "profile": "바이오 제약 배고픔 빵 과자 세포",
            "query": "바이오 제약 뉴스"
        },
        {
            "profile": "생명공학과 대학원생으로, 암 치료제 개발에 관심이 있습니다.",
            "query": "생명공학 뉴스"
        },
        {
            "profile": "인공지능 연구원으로, 머신러닝과 딥러닝 분야의 최신 동향을 추적합니다.",
            "query": "AI 기술 뉴스"
        },
        {
            "profile": "물리학자로, 양자컴퓨팅과 양자역학 연구를 하고 있습니다.",
            "query": "양자컴퓨팅 뉴스"
        },
        {
            "profile": "",
            "query": "최신 과학 뉴스"
        },
        {
            "profile": "화학과 학생입니다.",
            "query": ""  # 빈 쿼리 테스트
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        profile = test_case["profile"]
        query = test_case["query"]
        print(f"\n테스트 {i}: {profile[:50]}{'...' if len(profile) > 50 else ''}")
        print(f"설정된 쿼리: {query}")
        try:
            result = RAG(profile, query)
            print(f"결과: {result}")
        except Exception as e:
            print(f"오류: {e}")

def test_api_connection():
    """API 연결 테스트"""
    print("\n🔗 API 연결 테스트")
    print("=" * 50)
    
    try:
        import requests
        
        # API 연결 테스트
        test_url = os.environ.get('NEWS_RECOMMENDATION_API_URL', 'http://localhost:8001/recommendations')
        test_payload = {
            "query": "바이오 제약 뉴스",
            "profile_context": "바이오 제약 배고픔 빵 과자 세포",
            "num_recommendations": 1
        }
        
        print(f"API URL: {test_url}")
        print(f"테스트 페이로드: {test_payload}")
        
        response = requests.post(test_url, json=test_payload, timeout=10)
        
        print(f"응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"응답 데이터: {data}")
            
            if data.get("success"):
                print("✅ API 연결 성공!")
            else:
                print(f"❌ API 응답 실패: {data.get('error_message', '알 수 없는 오류')}")
        else:
            print(f"❌ HTTP 오류: {response.status_code}")
            print(f"응답 내용: {response.text}")
            
    except Exception as e:
        print(f"❌ API 연결 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

def test_user_fetch():
    """사용자 정보 조회 테스트"""
    print("\n📊 사용자 정보 조회 테스트")
    print("=" * 50)
    
    try:
        response = (
            supabase.table("profiles")
            .select("username, profile_context, slack_webhook_url, email, notification_time, notification_query")
            .execute()
        )
        
        print(f"조회된 사용자 수: {len(response.data)}")
        
        for user in response.data:
            username = user.get("username", "Unknown")
            profile_context = user.get("profile_context", "")
            slack_url = user.get("slack_webhook_url", "")
            email = user.get("email", "")
            notification_time = user.get("notification_time", "")
            notification_query = user.get("notification_query", "최신 과학 뉴스")
            
            print(f"\n사용자: {username}")
            print(f"  - 알림 시간: {notification_time}")
            print(f"  - 설정된 쿼리: {notification_query}")
            print(f"  - Slack: {'설정됨' if slack_url else '미설정'}")
            print(f"  - Email: {'설정됨' if email else '미설정'}")
            print(f"  - 프로필: {profile_context[:50]}{'...' if len(profile_context) > 50 else ''}")
            
    except Exception as e:
        print(f"사용자 정보 조회 중 오류: {e}")

def test_current_time_notifications():
    """현재 시간에 알림을 받을 사용자 확인"""
    print("\n⏰ 현재 시간 알림 대상 확인")
    print("=" * 50)
    
    try:
        now = datetime.now().strftime("%H:%M")
        print(f"현재 시간: {now}")
        
        response = (
            supabase.table("profiles")
            .select("username, profile_context, slack_webhook_url, email, notification_time, notification_query")
            .eq("notification_time", now)
            .execute()
        )
        
        if response.data:
            print(f"현재 시간({now})에 알림을 받을 사용자: {len(response.data)}명")
            for user in response.data:
                username = user.get("username", "Unknown")
                slack_url = user.get("slack_webhook_url", "")
                email = user.get("email", "")
                notification_query = user.get("notification_query", "최신 과학 뉴스")
                print(f"  - {username} (쿼리: {notification_query}, Slack: {'설정됨' if slack_url else '미설정'}, Email: {'설정됨' if email else '미설정'})")
        else:
            print(f"현재 시간({now})에 알림을 받을 사용자가 없습니다.")
            
    except Exception as e:
        print(f"현재 시간 알림 대상 확인 중 오류: {e}")

def main():
    """메인 테스트 함수"""
    print("AIGEN Science 간단한 알림 시스템 테스트")
    print("🔗 news_recommendation.py 함수 활용")
    print("=" * 60)
    
    while True:
        print("\n테스트 옵션:")
        print("1. 프로필 키워드 추출 테스트")
        print("2. API 연결 테스트")
        print("3. RAG 함수 테스트")
        print("4. 사용자 정보 조회 테스트")
        print("5. 현재 시간 알림 대상 확인")
        print("6. 전체 알림 시스템 테스트 (실제 전송 없음)")
        print("7. 종료")
        
        choice = input("\n선택하세요 (1-7): ").strip()
        
        if choice == "1":
            test_profile_keywords()
        elif choice == "2":
            test_api_connection()
        elif choice == "3":
            test_rag_function()
        elif choice == "4":
            test_user_fetch()
        elif choice == "5":
            test_current_time_notifications()
        elif choice == "6":
            print("\n🔄 전체 알림 시스템 테스트 (실제 전송 없음)")
            print("=" * 50)
            try:
                # 실제 전송 없이 로직만 테스트
                fetch_and_notify()
                print("✅ 테스트 완료!")
            except Exception as e:
                print(f"❌ 테스트 중 오류: {e}")
        elif choice == "7":
            print("테스트 종료")
            break
        else:
            print("잘못된 선택입니다.")

if __name__ == "__main__":
    main() 