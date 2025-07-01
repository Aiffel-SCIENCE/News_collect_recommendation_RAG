# src/news_articles_api/news_articles_api.py

import os
import sys
from typing import Optional, List
import traceback
from datetime import datetime

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

from fastapi import FastAPI, HTTPException, status # status 추가
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from pymongo import MongoClient
import certifi

# --- 프로젝트 루트 경로 설정 ---
_current_file_path = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file_path)))

if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# --- 내부 모듈 및 설정 임포트 ---
from src.config_loader.settings import SETTINGS

# --- 설정값 로드 ---
MONGO_URI = SETTINGS.get("MONGO_URI") #
NEWS_ARTICLES_API_SERVER_HOST = SETTINGS.get("NEWS_ARTICLES_API_SERVER_HOST", "0.0.0.0")
NEWS_ARTICLES_API_SERVER_PORT = SETTINGS.get("NEWS_ARTICLES_API_SERVER_PORT", 8002) 

# --- 전역 변수 (MongoDB 클라이언트) ---
mongo_client_articles: Optional[MongoClient] = None
articles_collection: Optional[any] = None 

# --- Pydantic 모델 정의 ---
class ArticleDetail(BaseModel):
    ID: str 
    title: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[str] = None
    source: Optional[str] = None
    keywords: Optional[List[str]] = []

class ArticleResponse(BaseModel):
    article: Optional[ArticleDetail] = None
    success: bool
    error_message: Optional[str] = None

# --- FastAPI 앱 인스턴스 ---
app = FastAPI(
    title="AIGEN Science - News Article Detail API",
    description="특정 뉴스 ID (URL 해시값)에 해당하는 상세 뉴스 정보를 제공합니다.",
    version="1.0.1" 
)

# --- CORS 미들웨어 추가 ---
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    os.environ.get('FRONTEND_URL', 'http://localhost:3000'),
    os.environ.get('FRONTEND_URL', 'http://localhost:3000') + '/ko',
    # 실제 프로덕션 프론트엔드 도메인 추가
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
    뉴스 아티클 API 서비스의 상태를 확인하는 헬스체크 엔드포인트.
    """
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# --- 서비스 초기화 함수 (MongoDB 연결) ---
def initialize_article_api_services():
    global mongo_client_articles, articles_collection
    print("--- 단일 뉴스 조회 API 서비스 초기화 중 ---")
    if MONGO_URI is None:
        print("❌ 단일 뉴스 조회 API: MONGO_URI가 설정되지 않았습니다.")
        raise RuntimeError("MONGO_URI is not set.")
    try:
        print("단일 뉴스 조회 API: MongoDB 연결 시도 중...")
        mongo_client_articles = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        mongo_client_articles.admin.command('ping') # 연결 테스트
        db_name = SETTINGS.get("MONGO_DB_NAME", "newsdb")
        collection_name = SETTINGS.get("MONGO_ARTICLES_COLLECTION_NAME", "articles")
        db = mongo_client_articles[db_name]
        articles_collection = db[collection_name]
        print(f"✅ 단일 뉴스 조회 API: MongoDB '{db_name}.{collection_name}' 컬렉션 연결 성공.")
    except Exception as e:
        mongo_client_articles = None
        articles_collection = None
        print(f"❌ 단일 뉴스 조회 API: MongoDB 연결 실패: {e}")
        raise RuntimeError(f"MongoDB connection failed: {e}")
    print("--- 단일 뉴스 조회 API 서비스 초기화 완료 ---")

# --- API 엔드포인트 ---
@app.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article_by_id(article_id: str):
    global articles_collection
    print(f"\n--- 단일 뉴스 조회 요청: article_id='{article_id}' ---")

    if not hasattr(app.state, 'services_ready') or not app.state.services_ready or articles_collection is None:
        print(f"CRITICAL: 단일 뉴스 조회 서비스가 초기화되지 않았습니다 (article_id: {article_id}).")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Article detail service is not available at the moment.")

    try:

        article_data_from_db = articles_collection.find_one({"ID": article_id})

        if not article_data_from_db:
            print(f"⚠️ 단일 뉴스 조회: article_id '{article_id}'에 해당하는 뉴스를 찾을 수 없습니다.")
            return ArticleResponse(article=None, success=False, error_message="Article not found.")



        article_detail_data = {
            "ID": article_data_from_db.get("ID"), 
            "title": article_data_from_db.get("title"),
            "url": article_data_from_db.get("url"),
            "summary": article_data_from_db.get("summary"),
            "content": article_data_from_db.get("content"),
            "published_at": article_data_from_db.get("published_at"),
            "source": article_data_from_db.get("source"),
            "keywords": article_data_from_db.get("keywords", []),
        }
        

        article_detail = ArticleDetail(**article_detail_data)

        print(f"✅ 단일 뉴스 조회: '{article_id}' 정보 반환 성공.")
        return ArticleResponse(article=article_detail, success=True)

    except HTTPException as http_exc: 
        raise http_exc
    except Exception as e:
        error_id = os.urandom(4).hex() # 간단한 오류 추적 ID
        print(f"❌ 단일 뉴스 조회 API 오류 발생 (Error ID: {error_id}): article_id='{article_id}'")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An internal server error occurred. (Error ID: {error_id})")


# --- 서버 시작 시 서비스 초기화 ---
@app.on_event("startup")
async def startup_event():
    app.state.services_ready = False 
    try:
        initialize_article_api_services()
        app.state.services_ready = True 
        print("✅ 단일 뉴스 조회 API 서비스가 성공적으로 시작되었습니다.")
    except RuntimeError as e:
        print(f"❌ 단일 뉴스 조회 API 서비스 시작 중 오류 발생: {e}")
        app.state.services_ready = False
    except Exception as e_global:
        print(f"❌ 단일 뉴스 조회 API 시작 중 예측하지 못한 전역 오류: {e_global}")
        app.state.services_ready = False


# --- 서버 종료 시 MongoDB 연결 해제 ---
@app.on_event("shutdown")
async def shutdown_event():
    global mongo_client_articles
    if mongo_client_articles:
        mongo_client_articles.close()
        print("단일 뉴스 조회 API: MongoDB 연결이 닫혔습니다.")

# --- 메인 실행 블록 ---
if __name__ == "__main__":
    print(f"--- AIGEN Science 단일 뉴스 조회 API 서버 시작 중 (호스트: {NEWS_ARTICLES_API_SERVER_HOST}, 포트: {NEWS_ARTICLES_API_SERVER_PORT}) ---")
    print(f"API Endpoint: GET /articles/{{article_id}}")
    print(f"Swagger UI: http://{NEWS_ARTICLES_API_SERVER_HOST}:{NEWS_ARTICLES_API_SERVER_PORT}/docs")
    uvicorn.run(app, host=NEWS_ARTICLES_API_SERVER_HOST, port=NEWS_ARTICLES_API_SERVER_PORT)


