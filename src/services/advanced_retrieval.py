"""
Advanced Retrieval 모듈
500+50 chunking과 Qwen3-Reranker를 사용한 고급 검색 시스템
"""

import sys
import os
from typing import List, Dict, Tuple, Any
import numpy as np
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import re

# 프로젝트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ..config_loader.settings import SETTINGS
from ..db.vector_db import PineconeDB

class AdvancedRetrieval:
    """고급 검색 시스템"""
    
    def __init__(self):
        self.vector_db = PineconeDB()
        self.embedding_model_name = SETTINGS.get('SHARED_EMBEDDING_MODEL_NAME', 'text-embedding-3-small')
        
        # 설정에서 reranker 관련 값 가져오기 - 더 관대한 설정으로 조정
        self.reranker_model_name = 'Qwen/Qwen3-Reranker-0.6B'  # 0.6B로 변경
        self.reranker_top_k = SETTINGS.get('RERANKER_TOP_K', 5)  # 3 -> 5로 증가
        self.dense_retrieval_top_k = SETTINGS.get('DENSE_RETRIEVAL_TOP_K', 10)  # 5 -> 10으로 증가
        
        # Qwen3-Reranker 초기화
        print(f"Qwen3-Reranker 모델 로딩 중: {self.reranker_model_name}")
        self.reranker_tokenizer = AutoTokenizer.from_pretrained(self.reranker_model_name)
        self.reranker_model = AutoModelForCausalLM.from_pretrained(self.reranker_model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.reranker_model = self.reranker_model.to(self.device)
        print(f"Qwen3-Reranker 모델을 {self.device.type.upper()}에서 실행합니다.")
        self.reranker_model.eval()
        print("Qwen3-Reranker 모델 로딩 완료.")
        print(f"검색 설정: Dense retrieval top_k={self.dense_retrieval_top_k}, Reranker top_k={self.reranker_top_k}")
    
    def create_500_50_chunks(self, text: str) -> List[str]:
        """500+50 chunking 방식으로 텍스트를 분할"""
        chunks = []
        
        # 텍스트를 문장 단위로 분할
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        current_chunk = ""
        overlap_text = ""
        
        for sentence in sentences:
            # 현재 문장을 추가했을 때의 길이 계산
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(test_chunk) <= 500:
                # 500자 이하면 현재 청크에 추가
                current_chunk = test_chunk
            else:
                # 500자 초과시 현재 청크 저장하고 새 청크 시작
                if current_chunk:
                    # 50자 overlap 추가
                    if overlap_text:
                        full_chunk = overlap_text + " " + current_chunk
                    else:
                        full_chunk = current_chunk
                    chunks.append(full_chunk)
                    
                    # 다음 청크를 위한 overlap 준비 (마지막 50자)
                    overlap_text = current_chunk[-50:] if len(current_chunk) > 50 else current_chunk
                    current_chunk = sentence
                else:
                    # 단일 문장이 500자를 초과하는 경우
                    current_chunk = sentence
        
        # 마지막 청크 처리
        if current_chunk:
            if overlap_text:
                full_chunk = overlap_text + " " + current_chunk
            else:
                full_chunk = current_chunk
            chunks.append(full_chunk)
        
        return chunks
    
    def dense_retrieval(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Dense retrieval로 top-k 문서 검색"""
        try:
            print(f"Dense retrieval 시작 - 쿼리: '{query}', top_k: {top_k}")
            
            # OpenAI 임베딩 생성
            from openai import OpenAI
            openai_client = OpenAI(api_key=SETTINGS['OPENAI_API_KEY'])
            
            print(f"임베딩 모델: {self.embedding_model_name}")
            response = openai_client.embeddings.create(
                model=self.embedding_model_name,
                input=query
            )
            query_vector = response.data[0].embedding
            print(f"쿼리 임베딩 생성 완료 - 벡터 크기: {len(query_vector)}")
            
            # Pinecone에서 검색
            documents = self.vector_db.query_vector(vector=query_vector, top_k=top_k)
            
            print(f"Dense retrieval 결과: {len(documents)}개 문서")
            
            # 검색 결과 상세 로그
            for i, doc in enumerate(documents):
                score = doc.get('score', 0)
                content = doc.get('metadata', {}).get('content', '')[:100]
                print(f"  문서 {i+1}: 점수={score:.4f}, 내용={content}...")
            
            return documents
            
        except Exception as e:
            print(f"Dense retrieval 중 오류 발생: {e}")
            return []
    
    def rerank_with_qwen(self, query: str, documents: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        """Qwen3-Reranker를 사용하여 문서 재순위화"""
        if not documents:
            return []
        
        try:
            print(f"Reranking 시작 - 쿼리: '{query}', 문서 수: {len(documents)}, top_k: {top_k}")
            
            # 문서 텍스트 추출
            doc_texts = [doc['metadata']['content'] for doc in documents]
            
            # Reranking 수행
            scores = []
            for i, doc_text in enumerate(doc_texts):
                print(f"  문서 {i+1} reranking 중...")
                
                # Qwen3-Reranker 입력 형식: "Query: {query} Document: {document}"
                input_text = f"Query: {query} Document: {doc_text}"
                
                # 토크나이징
                inputs = self.reranker_tokenizer(
                    input_text, 
                    return_tensors="pt", 
                    truncation=True, 
                    max_length=512
                )
                # device에 맞게 입력 이동
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                # 점수 계산
                with torch.no_grad():
                    outputs = self.reranker_model(**inputs)
                    # 마지막 토큰의 로짓을 점수로 사용
                    score = outputs.logits[0, -1, :].softmax(dim=-1).max().item()
                    scores.append(score)
                
                print(f"    문서 {i+1} 점수: {score:.4f}")
            
            # 점수와 문서를 함께 정렬
            doc_score_pairs = list(zip(documents, scores))
            doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
            
            # 상위 top_k개 반환
            reranked_docs = [doc for doc, score in doc_score_pairs[:top_k]]
            
            print(f"Reranking 완료: {len(reranked_docs)}개 문서 선택")
            
            # 최종 결과 로그
            for i, (doc, score) in enumerate(doc_score_pairs[:top_k]):
                content = doc.get('metadata', {}).get('content', '')[:100]
                print(f"  최종 {i+1}: 점수={score:.4f}, 내용={content}...")
            
            return reranked_docs
            
        except Exception as e:
            print(f"Reranking 중 오류 발생: {e}")
            # 오류 발생시 원본 순서로 반환
            return documents[:top_k]
    
    def advanced_retrieve(self, query: str, original_text: str = None) -> List[Dict[str, str]]:
        """고급 검색 수행: Dense retrieval + Reranking"""
        print("--- 고급 검색 시작 ---")
        print(f"검색 쿼리: '{query}'")
        
        # 1. Dense retrieval로 top 5개 검색
        print("1. Dense retrieval 수행 중...")
        documents = self.dense_retrieval(query, top_k=self.dense_retrieval_top_k)
        
        if not documents:
            print("검색된 문서가 없습니다.")
            return []
        
        print(f"Dense retrieval 결과: {len(documents)}개 문서")
        
        # 2. Qwen3-Reranker로 재순위화
        print("2. Qwen3-Reranker 재순위화 수행 중...")
        reranked_docs = self.rerank_with_qwen(query, documents, top_k=self.reranker_top_k)
        
        # 3. 문서 텍스트와 메타데이터 추출
        retrieved_docs = []
        for doc in reranked_docs:
            metadata = doc.get('metadata', {})
            content = metadata.get('content', '')
            url = metadata.get('url', '')  # URL 정보 추출
            
            retrieved_docs.append({
                'content': content,
                'url': url
            })
        
        print(f"최종 검색 결과: {len(retrieved_docs)}개 문서")
        
        # 최종 결과 상세 로그
        for i, doc in enumerate(retrieved_docs):
            print(f"  최종 문서 {i+1}: {doc['content'][:200]}...")
            if doc['url']:
                print(f"    URL: {doc['url']}")
        
        return retrieved_docs
    
    def process_text_with_chunks(self, text: str) -> List[str]:
        """텍스트를 500+50 chunking으로 처리"""
        print("500+50 chunking 처리 중...")
        chunks = self.create_500_50_chunks(text)
        print(f"생성된 청크 수: {len(chunks)}")
        
        # 청크 정보 출력
        for i, chunk in enumerate(chunks):
            print(f"청크 {i+1}: {len(chunk)}자")
        
        return chunks

def test_advanced_retrieval():
    """고급 검색 시스템 테스트"""
    print("고급 검색 시스템 테스트 시작")
    
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
    
    # AdvancedRetrieval 인스턴스 생성
    retrieval = AdvancedRetrieval()
    
    # 1. Chunking 테스트
    print("\n=== Chunking 테스트 ===")
    chunks = retrieval.process_text_with_chunks(test_text)
    
    # 2. 검색 테스트
    print("\n=== 검색 테스트 ===")
    query = "인공지능의 최신 기술 동향"
    results = retrieval.advanced_retrieve(query)
    
    print(f"\n검색 쿼리: {query}")
    print(f"검색 결과 수: {len(results)}")
    
    for i, result in enumerate(results, 1):
        print(f"\n--- 결과 {i} ---")
        print(result['content'][:200] + "..." if len(result['content']) > 200 else result['content'])
        if result['url']:
            print(f"    URL: {result['url']}")

if __name__ == "__main__":
    test_advanced_retrieval() 