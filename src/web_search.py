"""
웹검색 기능을 위한 모듈 - 네이버 웹 문서 검색 API 사용
"""

import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Optional
from urllib.parse import quote_plus
import time
import random
import os
import sys

# 프로젝트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config_loader.settings import SETTINGS

class WebSearchEngine:
    """웹검색 엔진 클래스 - 네이버 웹 문서 검색 API 사용"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        # 네이버 API 설정
        self.naver_client_id = SETTINGS.get('NAVER_CLIENT_ID', '')
        self.naver_client_secret = SETTINGS.get('NAVER_CLIENT_SECRET', '')
    
    def search_naver_webkr(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """네이버 웹 문서 검색 API 사용"""
        try:
            api_url = "https://openapi.naver.com/v1/search/webkr.json"
            headers = {
                'X-Naver-Client-Id': self.naver_client_id,
                'X-Naver-Client-Secret': self.naver_client_secret
            }
            
            params = {
                'query': query,
                'display': min(max_results, 10),  # 최대 10개
                'start': 1
            }
            
            response = self.session.get(api_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            if 'items' in data:
                for item in data['items'][:max_results]:
                    # HTML 태그 제거
                    title = BeautifulSoup(item.get('title', ''), 'html.parser').get_text()
                    description = BeautifulSoup(item.get('description', ''), 'html.parser').get_text()
                    
                    content = f"{title}\n{description}"
                    if content and len(content) > 30:
                        results.append({
                            'content': content,
                            'source': 'Naver Web Document Search',
                            'title': title,
                            'link': item.get('link', '')
                        })
            
            print(f"네이버 웹 문서 검색 결과: {len(results)}개")
            return results
            
        except Exception as e:
            print(f"네이버 웹 문서 검색 중 오류 발생: {e}")
            return []
    
    def search_naver_news(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """네이버 뉴스 API 검색"""
        try:
            api_url = "https://openapi.naver.com/v1/search/news.json"
            headers = {
                'X-Naver-Client-Id': self.naver_client_id,
                'X-Naver-Client-Secret': self.naver_client_secret
            }
            
            params = {
                'query': query,
                'display': min(max_results, 10),
                'start': 1,
                'sort': 'date'  # 최신순
            }
            
            response = self.session.get(api_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            if 'items' in data:
                for item in data['items'][:max_results]:
                    # HTML 태그 제거
                    title = BeautifulSoup(item.get('title', ''), 'html.parser').get_text()
                    description = BeautifulSoup(item.get('description', ''), 'html.parser').get_text()
                    
                    content = f"{title}\n{description}"
                    if content and len(content) > 30:
                        results.append({
                            'content': content,
                            'source': 'Naver News',
                            'title': title,
                            'link': item.get('link', '')
                        })
            
            print(f"네이버 뉴스 검색 결과: {len(results)}개")
            return results
            
        except Exception as e:
            print(f"네이버 뉴스 API 검색 중 오류: {e}")
            return []

    def search_multiple_sources(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """네이버 웹 문서 검색과 뉴스 검색 수행"""
        all_results = []
        
        # 검색 우선순위: 네이버 웹 문서 검색 -> 네이버 뉴스
        sources = [
            ('Naver Web Document', self.search_naver_webkr),
            ('Naver News', self.search_naver_news)
        ]
        
        for source_name, source_func in sources:
            try:
                print(f"{source_name} 검색 시작...")
                results = source_func(query, max_results)
                if results:
                    all_results.extend(results)
                    print(f"{source_name} 검색 성공: {len(results)}개 결과")
                else:
                    print(f"{source_name} 검색 결과 없음")
                
                # 충분한 결과가 있으면 중단
                if len(all_results) >= max_results * 2:
                    print(f"{source_name} 검색 후 충분한 결과 확보, 검색 중단")
                    break
                
                # 요청 간 간격 두기
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                print(f"검색 소스 {source_name}에서 오류: {e}")
                continue
        
        print(f"총 검색 결과: {len(all_results)}개")
        
        # 중복 제거 및 품질 필터링
        filtered_results = self._filter_results(all_results, max_results)
        
        return filtered_results
    
    def _filter_results(self, results: List[Dict[str, str]], max_results: int) -> List[Dict[str, str]]:
        """검색 결과 필터링 및 정리"""
        if not results:
            return []
        
        # 중복 제거 (내용 기반)
        seen_contents = set()
        unique_results = []
        
        for result in results:
            content = result['content']
            # 간단한 중복 제거 (첫 100자 기준)
            content_key = content[:100].lower()
            
            if content_key not in seen_contents and len(content) > 30:
                seen_contents.add(content_key)
                unique_results.append(result)
        
        # 품질 기준으로 정렬 (웹 문서 우선, 길이, 키워드 포함 등)
        def quality_score(result):
            content = result['content'].lower()
            source = result.get('source', '').lower()
            score = len(content)  # 기본 점수는 길이
            
            # 소스별 가중치 (웹 문서 우선)
            if 'web document' in source:
                score += 300
            elif 'news' in source:
                score += 200
            
            # 중요한 키워드가 포함된 경우 점수 추가
            important_words = ['정보', '데이터', '분석', '결과', '연구', '통계', '발표', '공개', '발표', '정책', '계획']
            for word in important_words:
                if word in content:
                    score += 30
            
            # 최신성 관련 키워드
            recent_words = ['2024', '최근', '최신', '새로운', '발표', '공개']
            for word in recent_words:
                if word in content:
                    score += 20
            
            return score
        
        # 품질 점수로 정렬
        sorted_results = sorted(unique_results, key=quality_score, reverse=True)
        
        return sorted_results[:max_results]

def perform_web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """웹검색 수행 함수"""
    search_engine = WebSearchEngine()
    results = search_engine.search_multiple_sources(query, max_results)
    
    # 텍스트와 URL 정보를 함께 반환
    return results

if __name__ == "__main__":
    # 테스트
    test_query = "인공지능 최신 동향"
    results = perform_web_search(test_query)
    
    print(f"검색 쿼리: {test_query}")
    print(f"검색 결과 수: {len(results)}")
    for i, result in enumerate(results, 1):
        print(f"\n--- 결과 {i} ---")
        print(f"소스: {result.get('source', 'Unknown')}")
        print(f"제목: {result.get('title', 'N/A')}")
        print(f"링크: {result.get('link', 'N/A')}")
        print(f"내용: {result['content'][:200] + '...' if len(result['content']) > 200 else result['content']}") 