# src/news_recommendation/news_recommendation.py

import os
import sys
from typing import List, Optional, Dict
import traceback
import time
from datetime import datetime

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(dotenv_path="/home/br631533333333_gmail_com/Aigen_science/.env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import numpy as np
from pymongo import MongoClient
import certifi
from openai import OpenAI

# --- 프로젝트 루트 경로 설정 ---
_current_file_path = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file_path)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# --- 프로젝트 모듈 및 설정 임포트 ---
from src.config_loader.settings import SETTINGS
from src.db.vector_db import PineconeDB

# --- 전역 변수 ---
embedding_model_name: Optional[str] = None
pinecone_manager: Optional[PineconeDB] = None
openai_client: Optional[OpenAI] = None
mongo_client: Optional[MongoClient] = None
articles_collection: Optional[any] = None
user_preferences_collection: Optional[any] = None

# --- Pydantic 모델 정의 ---
class RecommendationRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="사용자 ID. 개인화된 추천을 위해 필요합니다.")
    query: str = Field(..., description="사용자의 자연어 관심 분야 쿼리.", example="생명공학 분야의 새로운 치료제 개발 소식")
    profile_context: Optional[str] = Field(None, description="사용자의 프로필 컨텍스트. 'What would you like the AI to know about you'에 입력한 내용.")
    num_recommendations: Optional[int] = Field(10, ge=1, le=20, description="추천받을 뉴스 기사 개수. 기본값은 10개.")

class NewsItem(BaseModel):
    id: str
    title: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    published_at: Optional[str] = None
    similarity_score: float

class RecommendationResponse(BaseModel):
    user_query_keywords: List[str]
    recommended_news: List[NewsItem]
    success: bool
    error_message: Optional[str] = None

# --- FastAPI 앱 인스턴스 ---
app = FastAPI(
    title="AIGEN Science - Keyword-based News Recommendation API",
    description="사용자 쿼리 키워드와 기사 키워드 간의 유사도를 기반으로 뉴스를 추천합니다.",
    version="2.1.0"
)

# --- CORS 미들웨어 추가 ---
origins = [
    "http://localhost", "http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000",    "http://34.61.170.171:3000", "http://34.61.170.171:3000/ko"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health Check 엔드포인트 ---
@app.get("/health")
async def health_check():
    """
    뉴스 추천 API 서비스의 상태를 확인하는 헬스체크 엔드포인트.
    """
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# --- 서비스 초기화 함수 ---
def initialize_recommendation_services():
    global embedding_model_name, pinecone_manager, openai_client, articles_collection, mongo_client
    print("--- 키워드 기반 추천 서비스 초기화 중 ---")
    try:
        embedding_model_name = SETTINGS.get("SHARED_EMBEDDING_MODEL_NAME", "text-embedding-3-small")
        print(f"✅ 임베딩 모델 '{embedding_model_name}' 설정 완료.")
    except Exception as e:
        raise RuntimeError(f"임베딩 모델 설정 실패: {e}")

    try:
        pinecone_manager = PineconeDB()
        print("✅ PineconeDB 초기화 성공.")
    except Exception as e:
        raise RuntimeError(f"PineconeDB 초기화 실패: {e}")

    try:
        api_key = SETTINGS.get("OPENAI_API_KEY")
        if not api_key: raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        openai_client = OpenAI(api_key=api_key)
        print(f"✅ OpenAI 클라이언트 설정 완료.")
    except Exception as e:
        raise RuntimeError(f"OpenAI 클라이언트 초기화 실패: {e}")

    try:
        mongo_uri = SETTINGS.get("MONGO_URI")
        if not mongo_uri: raise ValueError("MONGO_URI가 설정되지 않았습니다.")
        mongo_client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
        db_name = SETTINGS.get("MONGO_DB_NAME", "newsdb")
        collection_name = SETTINGS.get("MONGO_ARTICLES_COLLECTION_NAME", "articles")
        articles_collection = mongo_client[db_name][collection_name]
        
        # 사용자 선호도 컬렉션 초기화
        user_preferences_collection = mongo_client[db_name]["user_preferences"]
        
        print(f"✅ MongoDB '{db_name}.{collection_name}' 연결 성공.")
        print(f"✅ 사용자 선호도 컬렉션 초기화 완료.")
    except Exception as e:
        raise RuntimeError(f"MongoDB 연결 실패: {e}")
    print("--- 키워드 기반 추천 서비스 초기화 완료 ---")

# --- 핵심 로직 함수 ---

def extract_keywords_from_query(query_text: str) -> List[str]:
    if not openai_client or not query_text: return []
    num_keywords, keyword_model = 5, SETTINGS.get("OPENAI_KEYWORD_MODEL", "gpt-4.1-nano")
    system_prompt = "당신은 주어진 사용자 질문에서 핵심 의도를 나타내는 주요 키워드를 추출하는 AI입니다."
    user_prompt = f"다음 텍스트에서 가장 중요한 키워드를 {num_keywords}개 이하로 추출해주세요. 쉼표로 구분된 리스트 형식으로만 답변해주세요.\n\n텍스트: {query_text}\n\n주요 키워드:"
    try:
        completion = openai_client.chat.completions.create(model=keyword_model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], temperature=0.2, max_tokens=60)
        return [kw.strip() for kw in completion.choices[0].message.content.strip().split(',') if kw.strip()]
    except Exception as e:
        print(f"LLM 쿼리 키워드 추출 중 오류: {e}"); return []

def embed_keywords_individually(keywords: List[str]) -> List[List[float]]:
    if not openai_client or not embedding_model_name or not keywords: return []
    embeddings = []
    for keyword in keywords:
        try:
            response = openai_client.embeddings.create(
                model=embedding_model_name,
                input=keyword
            )
            embeddings.append(response.data[0].embedding)
        except Exception as e:
            print(f"키워드 '{keyword}' 임베딩 중 오류: {e}")
            embeddings.append([])
    return embeddings

def calculate_keyword_similarity(user_embeddings: List[List[float]], article_embeddings: List[List[float]]) -> float:
    if not user_embeddings or not article_embeddings: return 0.0
    user_embeddings_np, article_embeddings_np = np.array(user_embeddings), np.array(article_embeddings)
    similarity_matrix = np.dot(user_embeddings_np, article_embeddings_np.T)
    max_scores_per_user_kw = np.max(similarity_matrix, axis=1)
    return float(np.mean(max_scores_per_user_kw))

# --- 사용자 개인화 함수들 ---

def get_user_interests(user_id: str) -> List[str]:
    """사용자의 저장된 관심사 키워드를 가져옵니다."""
    if not user_preferences_collection or not user_id:
        return []
    
    try:
        user_pref = user_preferences_collection.find_one({"user_id": user_id})
        if user_pref and "interests" in user_pref:
            return user_pref["interests"]
    except Exception as e:
        print(f"사용자 관심사 조회 중 오류: {e}")
    
    return []

def update_user_interests(user_id: str, interests: List[str]):
    """사용자의 관심사를 업데이트합니다."""
    if not user_preferences_collection or not user_id:
        return
    
    try:
        user_preferences_collection.update_one(
            {"user_id": user_id},
            {"$set": {"interests": interests, "updated_at": time.time()}},
            upsert=True
        )
        print(f"사용자 {user_id}의 관심사 업데이트 완료: {interests}")
    except Exception as e:
        print(f"사용자 관심사 업데이트 중 오류: {e}")

def extract_profile_keywords(profile_context: str) -> List[str]:
    """프로필 컨텍스트에서 키워드를 추출합니다."""
    if not profile_context or not openai_client:
        return []
    
    try:
        system_prompt = "당신은 사용자의 프로필 컨텍스트에서 관심사와 전문 분야를 나타내는 키워드를 추출하는 AI입니다."
        user_prompt = f"다음 사용자 프로필에서 관심사와 전문 분야를 나타내는 키워드를 5개 이하로 추출해주세요. 쉼표로 구분된 리스트 형식으로만 답변해주세요.\n\n프로필: {profile_context}\n\n관심사 키워드:"
        
        completion = openai_client.chat.completions.create(
            model=SETTINGS.get("OPENAI_KEYWORD_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=60
        )
        
        keywords = [kw.strip() for kw in completion.choices[0].message.content.strip().split(',') if kw.strip()]
        print(f"프로필 컨텍스트에서 추출된 키워드: {keywords}")
        return keywords
    except Exception as e:
        print(f"프로필 컨텍스트 키워드 추출 중 오류: {e}")
        return []

def create_personalized_query(user_id: str, base_query: str, profile_context: str = None) -> str:
    """사용자의 관심사, 프로필 컨텍스트와 기본 쿼리를 결합하여 개인화된 쿼리를 생성합니다."""
    query_parts = [base_query]
    
    # 1. 기존 사용자 관심사 추가
    user_interests = get_user_interests(user_id)
    if user_interests:
        query_parts.extend(user_interests)
    
    # 2. 프로필 컨텍스트에서 키워드 추출하여 추가
    if profile_context:
        profile_keywords = extract_profile_keywords(profile_context)
        if profile_keywords:
            query_parts.extend(profile_keywords)
    
    # 모든 요소를 결합
    personalized_query = " ".join(query_parts)
    print(f"개인화된 쿼리 생성: {personalized_query}")
    print(f"  - 기본 쿼리: {base_query}")
    print(f"  - 사용자 관심사: {user_interests}")
    print(f"  - 프로필 키워드: {profile_keywords if profile_context else '없음'}")
    
    return personalized_query

@app.on_event("startup")
async def startup_event():
    try:
        initialize_recommendation_services(); app.state.services_ready = True
    except RuntimeError as e:
        print(f"CRITICAL: 서비스 초기화 실패: {e}"); app.state.services_ready = False

@app.on_event("shutdown")
async def shutdown_event():
    if mongo_client: mongo_client.close(); print("MongoDB 연결이 닫혔습니다.")

@app.post("/recommendations", response_model=RecommendationResponse)
async def get_news_recommendations(request: RecommendationRequest):
    if not app.state.services_ready:
        raise HTTPException(status_code=503, detail="추천 서비스가 준비되지 않았습니다.")

    # 1. 개인화된 쿼리 생성
    personalized_query = request.query
    if request.user_id:
        personalized_query = create_personalized_query(request.user_id, request.query, request.profile_context)
        print(f"사용자 {request.user_id}의 개인화된 쿼리: {personalized_query}")

    # 2. 사용자 쿼리에서 키워드 추출 및 개별 임베딩
    user_keywords = extract_keywords_from_query(personalized_query)
    if not user_keywords:
        return RecommendationResponse(user_query_keywords=[], recommended_news=[], success=False, error_message="쿼리에서 키워드를 추출할 수 없습니다.")
    
    # 3. 사용자 관심사 업데이트 (새로운 키워드 학습)
    if request.user_id:
        # 프로필 컨텍스트에서 키워드 추출하여 사용자 관심사에 저장
        if request.profile_context:
            profile_keywords = extract_profile_keywords(request.profile_context)
            if profile_keywords:
                # 기존 관심사와 프로필 키워드를 결합
                existing_interests = get_user_interests(request.user_id)
                combined_interests = list(set(existing_interests + profile_keywords))
                update_user_interests(request.user_id, combined_interests)
                print(f"프로필 키워드를 사용자 관심사에 추가: {profile_keywords}")
        
        # 쿼리에서 추출한 키워드도 업데이트
        update_user_interests(request.user_id, user_keywords)
    
    user_keyword_embeddings = embed_keywords_individually(user_keywords)

    # 4. Pinecone에서 전체 쿼리 임베딩 기반으로 후보군 1차 필터링
    query_content_embedding = embed_keywords_individually([personalized_query])[0]
    candidate_matches = pinecone_manager.query_vector(
        vector=query_content_embedding,
        top_k=500,  # [수정됨] 2차 랭킹을 위해 후보군을 500개로 확보
        include_metadata=False
    )
    candidate_ids = [match.id for match in candidate_matches]

    # 5. MongoDB에서 후보 기사의 상세 정보 조회
    articles_from_mongo = list(articles_collection.find(
        {"ID": {"$in": candidate_ids}},
        {"ID": 1, "title": 1, "url": 1, "summary": 1, "published_at": 1, "llm_individual_keyword_embeddings": 1}
    ))

    # 6. 각 후보 기사별로 키워드 유사도 점수 계산 (2차 정밀 랭킹)
    scored_news_items = []
    for article in articles_from_mongo:
        article_keyword_embeddings = article.get("llm_individual_keyword_embeddings")
        if not article_keyword_embeddings: continue
        similarity_score = calculate_keyword_similarity(user_keyword_embeddings, article_keyword_embeddings)
        scored_news_items.append({
            "id": article.get("ID"), "title": article.get("title"), "url": article.get("url"),
            "summary": article.get("summary"), "published_at": article.get("published_at"),
            "similarity_score": similarity_score,
        })

    # 7. 최종 추천 목록 생성
    scored_news_items.sort(key=lambda x: x["similarity_score"], reverse=True)
    final_recommendations = [NewsItem(**item) for item in scored_news_items[:request.num_recommendations]]

    return RecommendationResponse(
        user_query_keywords=user_keywords,
        recommended_news=final_recommendations,
        success=True
    )

if __name__ == "__main__":
    server_port = SETTINGS.get("NEWS_REC_SERVER_PORT", 8001)
    print(f"--- AIGEN Science 키워드 기반 추천 API 서버 시작 ---")
    print(f"Swagger UI: http://127.0.0.1:{server_port}/docs")
    print(f"API Endpoint: POST /recommendations")
    uvicorn.run(app, host="0.0.0.0", port=server_port)
