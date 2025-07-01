#!/usr/bin/env python3
"""
실제 사용자 데이터 확인 스크립트
"""

from supabase import create_client, Client
import json
import os
from datetime import datetime

# Supabase 설정
url: str = os.environ.get('SUPABASE_URL', '<your-supabase-url>')
key: str = os.environ.get('SUPABASE_ANON_KEY', '<your-supabase-anon-key>')
supabase: Client = create_client(url, key)

def check_all_users():
    """모든 사용자 정보 확인"""
    print("👥 모든 사용자 정보 확인")
    print("=" * 60)
    
    try:
        response = (
            supabase.table("profiles")
            .select("*")
            .execute()
        )
        
        print(f"총 사용자 수: {len(response.data)}")
        print()
        
        for i, user in enumerate(response.data, 1):
            print(f"사용자 {i}:")
            print(f"  - ID: {user.get('id', 'N/A')}")
            print(f"  - Username: {user.get('username', 'N/A')}")
            print(f"  - Display Name: {user.get('display_name', 'N/A')}")
            print(f"  - Profile Context: {user.get('profile_context', 'N/A')}")
            print(f"  - Slack Webhook: {'설정됨' if user.get('slack_webhook_url') else '미설정'}")
            print(f"  - Email: {user.get('email', '미설정')}")
            print(f"  - Notification Time: {user.get('notification_time', '미설정')}")
            print(f"  - Notification Query: {user.get('notification_query', '기본값')}")
            print(f"  - Created At: {user.get('created_at', 'N/A')}")
            print(f"  - Updated At: {user.get('updated_at', 'N/A')}")
            print("-" * 40)

def check_specific_user(username):
    """특정 사용자 정보 확인"""
    print(f"🔍 사용자 '{username}' 정보 확인")
    print("=" * 60)
    
    try:
        response = (
            supabase.table("profiles")
            .select("*")
            .eq("username", username)
            .execute()
        )
        
        if response.data:
            user = response.data[0]
            print("사용자 정보:")
            print(json.dumps(user, indent=2, ensure_ascii=False))
        else:
            print(f"사용자 '{username}'를 찾을 수 없습니다.")
            
    except Exception as e:
        print(f"사용자 정보 조회 중 오류: {e}")

def check_notification_settings():
    """알림 설정이 완료된 사용자 확인"""
    print("🔔 알림 설정이 완료된 사용자 확인")
    print("=" * 60)
    
    try:
        response = (
            supabase.table("profiles")
            .select("username, profile_context, slack_webhook_url, email, notification_time, notification_query")
            .execute()
        )
        
        notification_ready_users = []
        
        for user in response.data:
            username = user.get("username")
            slack_url = user.get("slack_webhook_url")
            email = user.get("email")
            notification_time = user.get("notification_time")
            profile_context = user.get("profile_context")
            
            # 알림 설정이 완료된 사용자 (시간 + 채널 중 하나)
            if notification_time and (slack_url or email):
                notification_ready_users.append({
                    "username": username,
                    "notification_time": notification_time,
                    "slack": bool(slack_url),
                    "email": bool(email),
                    "profile_context": profile_context
                })
        
        print(f"알림 설정 완료된 사용자: {len(notification_ready_users)}명")
        print()
        
        for user in notification_ready_users:
            print(f"사용자: {user['username']}")
            print(f"  - 알림 시간: {user['notification_time']}")
            print(f"  - Slack: {'설정됨' if user['slack'] else '미설정'}")
            print(f"  - Email: {'설정됨' if user['email'] else '미설정'}")
            print(f"  - 프로필: {user['profile_context'][:50]}{'...' if len(user['profile_context']) > 50 else ''}")
            print("-" * 30)

def update_user_notification_settings():
    """사용자 알림 설정 업데이트"""
    print("⚙️ 사용자 알림 설정 업데이트")
    print("=" * 60)
    
    username = input("업데이트할 사용자명: ").strip()
    
    if not username:
        print("사용자명을 입력해주세요.")
        return
    
    try:
        # 현재 사용자 정보 확인
        response = (
            supabase.table("profiles")
            .select("username, profile_context, slack_webhook_url, email, notification_time, notification_query")
            .eq("username", username)
            .execute()
        )
        
        if not response.data:
            print(f"사용자 '{username}'를 찾을 수 없습니다.")
            return
        
        user = response.data[0]
        print(f"현재 설정:")
        print(f"  - Slack Webhook: {user.get('slack_webhook_url', '미설정')}")
        print(f"  - Email: {user.get('email', '미설정')}")
        print(f"  - Notification Time: {user.get('notification_time', '미설정')}")
        print(f"  - Notification Query: {user.get('notification_query', '기본값')}")
        
        # 새로운 설정 입력
        print("\n새로운 설정 (변경하지 않으려면 엔터):")
        
        new_slack_url = input("Slack Webhook URL: ").strip()
        new_email = input("Email: ").strip()
        new_time = input("Notification Time (HH:MM): ").strip()
        new_query = input("Notification Query: ").strip()
        
        # 업데이트할 데이터 준비
        update_data = {}
        if new_slack_url:
            update_data["slack_webhook_url"] = new_slack_url
        if new_email:
            update_data["email"] = new_email
        if new_time:
            update_data["notification_time"] = new_time
        if new_query:
            update_data["notification_query"] = new_query
        
        if update_data:
            # 업데이트 실행
            update_response = (
                supabase.table("profiles")
                .update(update_data)
                .eq("username", username)
                .execute()
            )
            
            if update_response.data:
                print("✅ 사용자 설정이 업데이트되었습니다.")
            else:
                print("❌ 업데이트에 실패했습니다.")
        else:
            print("변경사항이 없습니다.")
            
    except Exception as e:
        print(f"업데이트 중 오류: {e}")

def main():
    """메인 함수"""
    print("AIGEN Science 사용자 데이터 확인 도구")
    print("=" * 60)
    
    while True:
        print("\n옵션:")
        print("1. 모든 사용자 정보 확인")
        print("2. 특정 사용자 정보 확인")
        print("3. 알림 설정 완료된 사용자 확인")
        print("4. 사용자 알림 설정 업데이트")
        print("5. 종료")
        
        choice = input("\n선택하세요 (1-5): ").strip()
        
        if choice == "1":
            check_all_users()
        elif choice == "2":
            username = input("확인할 사용자명: ").strip()
            if username:
                check_specific_user(username)
            else:
                print("사용자명을 입력해주세요.")
        elif choice == "3":
            check_notification_settings()
        elif choice == "4":
            update_user_notification_settings()
        elif choice == "5":
            print("종료합니다.")
            break
        else:
            print("잘못된 선택입니다.")

if __name__ == "__main__":
    main() 