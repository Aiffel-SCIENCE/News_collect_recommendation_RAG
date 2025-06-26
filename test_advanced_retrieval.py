#!/usr/bin/env python3
"""
Advanced Retrieval 시스템 테스트 스크립트
"""

import sys
import os

# 프로젝트 경로 추가
sys.path.append(os.path.abspath('.'))

def test_advanced_retrieval():
    """Advanced Retrieval 시스템 테스트"""
    print("Advanced Retrieval 시스템 테스트 시작")
    
    try:
        from src.advanced_retrieval import AdvancedRetrieval
        
        # AdvancedRetrieval 인스턴스 생성
        print("AdvancedRetrieval 인스턴스 생성 중...")
        retrieval = AdvancedRetrieval()
        
        # 테스트 쿼리
        test_query = "인공지능 최신 기술 동향"
        print(f"\n테스트 쿼리: {test_query}")
        
        # 고급 검색 수행
        print("고급 검색 수행 중...")
        results = retrieval.advanced_retrieve(test_query)
        
        print(f"\n검색 결과 수: {len(results)}")
        for i, result in enumerate(results, 1):
            print(f"\n--- 결과 {i} ---")
            print(result[:300] + "..." if len(result) > 300 else result)
            
    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def test_chunking():
    """500+50 chunking 테스트"""
    print("\n" + "="*50)
    print("500+50 Chunking 테스트")
    print("="*50)
    
    try:
        from src.advanced_retrieval import AdvancedRetrieval
        
        retrieval = AdvancedRetrieval()
        
        # 테스트 텍스트
        test_text = """
        인공지능(AI)은 컴퓨터 시스템이 인간의 지능을 모방하여 학습하고, 추론하고, 문제를 해결할 수 있도록 하는 기술입니다. 
        최근 몇 년간 딥러닝 기술의 발전으로 AI는 이미지 인식, 자연어 처리, 음성 인식 등 다양한 분야에서 혁신적인 성과를 보여주고 있습니다.
        
        머신러닝은 AI의 한 분야로, 데이터로부터 패턴을 학습하여 예측이나 분류를 수행하는 기술입니다. 
        지도학습, 비지도학습, 강화학습 등 다양한 학습 방법이 있으며, 각각의 특성에 맞는 문제에 적용됩니다.
        
        자연어 처리(NLP)는 컴퓨터가 인간의 언어를 이해하고 처리할 수 있도록 하는 AI 기술입니다. 
        텍스트 분류, 감정 분석, 기계 번역, 질의응답 시스템 등 다양한 응용 분야가 있습니다.
        
        컴퓨터 비전은 컴퓨터가 이미지나 비디오에서 의미 있는 정보를 추출하고 이해하는 기술입니다. 
        객체 인식, 얼굴 인식, 의료 영상 분석 등에서 활용되고 있습니다.
        
        강화학습은 에이전트가 환경과 상호작용하며 보상을 최대화하는 행동을 학습하는 방법입니다. 
        게임 AI, 로봇 제어, 자율주행차 등에서 중요한 역할을 하고 있습니다.
        """
        
        print("원본 텍스트 길이:", len(test_text))
        
        # Chunking 수행
        chunks = retrieval.process_text_with_chunks(test_text)
        
        print(f"\n생성된 청크 수: {len(chunks)}")
        for i, chunk in enumerate(chunks, 1):
            print(f"청크 {i}: {len(chunk)}자")
            print(f"내용: {chunk[:100]}...")
            print("-" * 30)
            
    except Exception as e:
        print(f"Chunking 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Advanced Retrieval 시스템 테스트 시작")
    
    # Chunking 테스트
    test_chunking()
    
    # Advanced Retrieval 테스트
    test_advanced_retrieval()
    
    print("\n테스트 완료!") 