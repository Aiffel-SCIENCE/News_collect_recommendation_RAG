#!/usr/bin/env python3
"""
새로운 LangGraph 워크플로우 테스트 스크립트 (Advanced Retrieval 포함)
"""

import sys
import os
from typing import Dict, Any

# 프로젝트 경로 추가
sys.path.append(os.path.abspath('.'))

from src.rag_graph.graph_rag import graph, GraphState

def test_advanced_retrieval():
    """Advanced Retrieval 시스템 테스트"""
    print("\n" + "="*60)
    print("Advanced Retrieval 시스템 테스트")
    print("="*60)
    
    try:
        from src.services.advanced_retrieval import AdvancedRetrieval
        
        # AdvancedRetrieval 인스턴스 생성
        retrieval = AdvancedRetrieval()
        
        # 테스트 쿼리
        test_query = "인공지능 최신 기술 동향"
        print(f"테스트 쿼리: {test_query}")
        
        # 고급 검색 수행
        results = retrieval.advanced_retrieve(test_query)
        
        print(f"검색 결과 수: {len(results)}")
        for i, result in enumerate(results, 1):
            print(f"\n--- 결과 {i} ---")
            print(result[:300] + "..." if len(result) > 300 else result)
            
    except Exception as e:
        print(f"Advanced Retrieval 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

def test_langgraph_workflow():
    """LangGraph 워크플로우 테스트"""
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "Text 의도 - RAG 답변 가능한 쿼리",
            "query": "최근 뉴스에서 인공지능 관련 기사가 있나요?",
            "user_id": "test_user_1",
            "expected_intent": "text"
        },
        {
            "name": "Text 의도 - 웹검색이 필요한 쿼리",
            "query": "2024년 최신 AI 기술 동향은 무엇인가요?",
            "user_id": "test_user_2",
            "expected_intent": "text"
        },
        {
            "name": "Dashboard 의도 - 차트 생성 요청",
            "query": "AI 기술 동향을 차트로 보여줘",
            "user_id": "test_user_3",
            "expected_intent": "dashboard"
        },
        {
            "name": "React 의도 - 시각화 요청",
            "query": "인공지능 발전 과정을 시각화해줘",
            "user_id": "test_user_4",
            "expected_intent": "react"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"테스트 케이스 {i}: {test_case['name']}")
        print(f"{'='*60}")
        
        # 초기 상태 설정
        initial_state = GraphState(
            user_id=test_case["user_id"],
            query=test_case["query"],
            chat_history=[],
            rewritten_query="",
            documents=[],
            generation="",
            intent="",
            is_generation_positive=False,
            chart_data={},
            dashboard_html="",
            react_code="",
            response_metadata={},
            web_search_query="",
            web_search_results=[],
            web_search_answer="",
            final_answer="",
            answer_source=""
        )
        
        try:
            # 그래프 실행
            print(f"쿼리: {test_case['query']}")
            print(f"예상 의도: {test_case['expected_intent']}")
            print("워크플로우 실행 중...")
            
            result = graph.invoke(initial_state)
            
            # 결과 출력
            print(f"\n--- 결과 ---")
            print(f"실제 의도: {result.get('intent', 'N/A')}")
            print(f"LLM 정보 충족도 평가: {'충분함' if result.get('is_generation_positive', False) else '부족함'}")
            print(f"최종 답변: {result.get('final_answer', 'N/A')}")
            print(f"답변 소스: {result.get('answer_source', 'N/A')}")
            
            if result.get('documents'):
                print(f"RAG 문서 수: {len(result.get('documents', []))}")
                print("RAG 문서 미리보기:")
                for i, doc in enumerate(result.get('documents', [])[:2], 1):
                    print(f"  문서 {i}: {doc[:100]}{'...' if len(doc) > 100 else ''}")
            
            if result.get('web_search_results'):
                print(f"웹검색 결과 수: {len(result.get('web_search_results', []))}")
                print("웹검색 결과 미리보기:")
                for i, doc in enumerate(result.get('web_search_results', [])[:2], 1):
                    print(f"  결과 {i}: {doc[:100]}{'...' if len(doc) > 100 else ''}")
            
            # 의도 일치 확인
            actual_intent = result.get('intent', 'N/A')
            expected_intent = test_case['expected_intent']
            if actual_intent == expected_intent:
                print(f"✅ 의도 일치: {actual_intent}")
            else:
                print(f"❌ 의도 불일치: 예상 {expected_intent}, 실제 {actual_intent}")
            
            print(f"\n{'='*60}")
            
        except Exception as e:
            print(f"테스트 실행 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()

def test_web_search_module():
    """웹검색 모듈 테스트"""
    print("\n" + "="*60)
    print("웹검색 모듈 테스트")
    print("="*60)
    
    try:
        from src.web_search import perform_web_search
        
        test_query = "인공지능 최신 동향 2024"
        print(f"테스트 쿼리: {test_query}")
        
        results = perform_web_search(test_query, max_results=3)
        
        print(f"검색 결과 수: {len(results)}")
        for i, result in enumerate(results, 1):
            print(f"\n--- 결과 {i} ---")
            print(result[:300] + "..." if len(result) > 300 else result)
            
    except Exception as e:
        print(f"웹검색 모듈 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("LangGraph 워크플로우 테스트 시작")
    
    # Advanced Retrieval 테스트
    test_advanced_retrieval()
    
    # 웹검색 모듈 테스트
    test_web_search_module()
    
    # 전체 워크플로우 테스트
    test_langgraph_workflow()
    
    print("\n테스트 완료!") 