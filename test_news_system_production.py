#!/usr/bin/env python3
"""
프로덕션 환경 뉴스 시스템 API 연결 상태 테스트 스크립트
"""

import requests
import json
import time
from typing import Dict, Any

# 프로덕션 서버 설정
PRODUCTION_HOST = "34.61.170.171"

def test_api_connection(url: str, name: str) -> Dict[str, Any]:
    """API 연결 상태를 테스트합니다."""
    try:
        print(f"🔍 {name} 연결 테스트 중... ({url})")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ {name} 연결 성공!")
            return {"status": "success", "url": url, "name": name}
        else:
            print(f"❌ {name} 연결 실패 (상태 코드: {response.status_code})")
            return {"status": "failed", "url": url, "name": name, "status_code": response.status_code}
            
    except requests.exceptions.ConnectionError:
        print(f"❌ {name} 연결 실패 (서비스가 실행되지 않음)")
        return {"status": "failed", "url": url, "name": name, "error": "Connection refused"}
    except requests.exceptions.Timeout:
        print(f"❌ {name} 연결 실패 (타임아웃)")
        return {"status": "failed", "url": url, "name": name, "error": "Timeout"}
    except Exception as e:
        print(f"❌ {name} 연결 실패 (오류: {e})")
        return {"status": "failed", "url": url, "name": name, "error": str(e)}

def test_news_recommendation_api():
    """뉴스 추천 API를 테스트합니다."""
    url = f"http://{PRODUCTION_HOST}:8001/recommendations"
    test_data = {
        "user_id": "test_user",
        "query": "과학 기술 뉴스",
        "num_recommendations": 3
    }
    
    try:
        print("🔍 뉴스 추천 API 테스트 중...")
        response = requests.post(url, json=test_data, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"✅ 뉴스 추천 API 성공! {len(data.get('recommended_news', []))}개 뉴스 추천")
                return {"status": "success", "recommendations_count": len(data.get('recommended_news', []))}
            else:
                print(f"❌ 뉴스 추천 API 실패: {data.get('error_message', 'Unknown error')}")
                return {"status": "failed", "error": data.get('error_message')}
        else:
            print(f"❌ 뉴스 추천 API 실패 (상태 코드: {response.status_code})")
            return {"status": "failed", "status_code": response.status_code}
            
    except Exception as e:
        print(f"❌ 뉴스 추천 API 테스트 실패: {e}")
        return {"status": "failed", "error": str(e)}

def test_news_article_api():
    """뉴스 상세 API를 테스트합니다."""
    # 먼저 추천 API에서 뉴스 ID를 가져옴
    recommendation_result = test_news_recommendation_api()
    
    if recommendation_result.get("status") != "success":
        print("❌ 뉴스 상세 API 테스트를 위해 먼저 추천 API가 필요합니다.")
        return {"status": "failed", "error": "Recommendation API not available"}
    
    try:
        # 추천 API에서 뉴스 ID 가져오기
        url = f"http://{PRODUCTION_HOST}:8001/recommendations"
        test_data = {
            "user_id": "test_user",
            "query": "과학 기술 뉴스",
            "num_recommendations": 1
        }
        
        response = requests.post(url, json=test_data, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("recommended_news") and len(data["recommended_news"]) > 0:
                article_id = data["recommended_news"][0]["id"]
                
                # 상세 API 테스트
                detail_url = f"http://{PRODUCTION_HOST}:8002/articles/{article_id}"
                print(f"🔍 뉴스 상세 API 테스트 중... (ID: {article_id})")
                
                detail_response = requests.get(detail_url, timeout=10)
                
                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    if detail_data.get("success") and detail_data.get("article"):
                        print("✅ 뉴스 상세 API 성공!")
                        return {"status": "success", "article_id": article_id}
                    else:
                        print(f"❌ 뉴스 상세 API 실패: {detail_data.get('error_message', 'Unknown error')}")
                        return {"status": "failed", "error": detail_data.get('error_message')}
                else:
                    print(f"❌ 뉴스 상세 API 실패 (상태 코드: {detail_response.status_code})")
                    return {"status": "failed", "status_code": detail_response.status_code}
            else:
                print("❌ 추천된 뉴스가 없습니다.")
                return {"status": "failed", "error": "No recommended news available"}
        else:
            print("❌ 뉴스 ID를 가져올 수 없습니다.")
            return {"status": "failed", "error": "Cannot get news ID"}
            
    except Exception as e:
        print(f"❌ 뉴스 상세 API 테스트 실패: {e}")
        return {"status": "failed", "error": str(e)}

def test_rag_api():
    """RAG API를 테스트합니다."""
    url = f"http://{PRODUCTION_HOST}:8010/rag-chat"
    test_data = {
        "user_id": "test_user",
        "query": "최근 과학 기술 뉴스에 대해 알려주세요"
    }
    
    try:
        print("🔍 RAG API 테스트 중...")
        response = requests.post(url, json=test_data, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("text"):
                print("✅ RAG API 성공!")
                print(f"답변 길이: {len(data['text'])} 문자")
                return {"status": "success", "response_length": len(data['text'])}
            else:
                print("❌ RAG API 실패: 응답에 텍스트가 없습니다.")
                return {"status": "failed", "error": "No text in response"}
        else:
            print(f"❌ RAG API 실패 (상태 코드: {response.status_code})")
            return {"status": "failed", "status_code": response.status_code}
            
    except Exception as e:
        print(f"❌ RAG API 테스트 실패: {e}")
        return {"status": "failed", "error": str(e)}

def test_frontend_connection():
    """프론트엔드 연결을 테스트합니다."""
    url = f"http://{PRODUCTION_HOST}:3000"
    
    try:
        print("🔍 프론트엔드 연결 테스트 중...")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("✅ 프론트엔드 연결 성공!")
            return {"status": "success", "url": url}
        else:
            print(f"❌ 프론트엔드 연결 실패 (상태 코드: {response.status_code})")
            return {"status": "failed", "url": url, "status_code": response.status_code}
            
    except Exception as e:
        print(f"❌ 프론트엔드 연결 실패: {e}")
        return {"status": "failed", "url": url, "error": str(e)}

def main():
    """메인 테스트 함수"""
    print("🚀 프로덕션 뉴스 시스템 API 연결 상태 테스트 시작")
    print(f"📍 서버: {PRODUCTION_HOST}")
    print("=" * 60)
    
    # 기본 연결 테스트
    apis = [
        (f"http://{PRODUCTION_HOST}:3000", "프론트엔드"),
        (f"http://{PRODUCTION_HOST}:8001/docs", "뉴스 추천 API (Swagger)"),
        (f"http://{PRODUCTION_HOST}:8002/docs", "뉴스 상세 API (Swagger)"),
        (f"http://{PRODUCTION_HOST}:8010/docs", "RAG API (Swagger)"),
    ]
    
    connection_results = []
    for url, name in apis:
        result = test_api_connection(url, name)
        connection_results.append(result)
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("📊 기능 테스트")
    print("=" * 60)
    
    # 기능 테스트
    recommendation_result = test_news_recommendation_api()
    time.sleep(2)
    
    article_result = test_news_article_api()
    time.sleep(2)
    
    rag_result = test_rag_api()
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📋 테스트 결과 요약")
    print("=" * 60)
    
    successful_connections = sum(1 for r in connection_results if r["status"] == "success")
    print(f"🔗 서비스 연결: {successful_connections}/{len(connection_results)} 성공")
    
    print(f"🌐 프론트엔드: {'✅' if connection_results[0]['status'] == 'success' else '❌'}")
    print(f"📰 뉴스 추천: {'✅' if recommendation_result['status'] == 'success' else '❌'}")
    print(f"📄 뉴스 상세: {'✅' if article_result['status'] == 'success' else '❌'}")
    print(f"🤖 RAG 기능: {'✅' if rag_result['status'] == 'success' else '❌'}")
    
    # 문제 해결 가이드
    if successful_connections < len(connection_results):
        print("\n🔧 문제 해결 가이드:")
        print("1. 서버에서 Docker 서비스가 실행 중인지 확인:")
        print("   ssh [사용자명]@34.61.170.171")
        print("   docker-compose ps")
        print("2. 서비스 재시작:")
        print("   docker-compose restart")
        print("3. 로그 확인:")
        print("   docker-compose logs [서비스명]")
        print("4. 전체 재시작:")
        print("   docker-compose down && docker-compose up -d")
        print("5. 방화벽 설정 확인:")
        print("   - 포트 3000, 8001, 8002, 8010이 열려있는지 확인")
    
    print(f"\n🌐 웹사이트 접속: http://{PRODUCTION_HOST}:3000")

if __name__ == "__main__":
    main() 