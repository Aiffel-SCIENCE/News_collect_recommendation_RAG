# aigen-science_RAG

#  AIGEN Science

AI 기반 정보 수집, 요약, 개인화 시스템 개발 프로젝트입니다.  
LLM과 RAG(Retrieval-Augmented Generation) 구조를 활용하여 사용자가 원하는 정보를 빠르게 가공하고 전달하는 것을 목표로 합니다.

---

## 🔧 환경 설정

### 1. 환경 변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 환경 변수들을 설정하세요:

```bash
# MongoDB 설정
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=newsdb
MONGO_ARTICLES_COLLECTION_NAME=articles
MONGO_BLACKLIST_COLLECTION_NAME=Filter3

# Redis 설정
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_BLOCK_TIMEOUT=30

# API 키 및 민감 정보
DART_API_KEY=your_dart_api_key_here
NAVER_CLIENT_ID=your_naver_client_id_here
NAVER_CLIENT_SECRET=your_naver_client_secret_here
OPENAI_API_KEY=your_openai_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here

# Pinecone 환경 정보
PINECONE_ENVIRONMENT=us-east-1
PINECONE_INDEX_NAME=news-embedding-3

# Supabase 설정
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here

# 알림 시스템 설정
BREVO_API_KEY=your_brevo_api_key_here

# 뉴스 추천 API 설정
NEWS_RECOMMENDATION_API_URL=http://news-recommendation-api:8001

# 기타 설정
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
API_URL=http://llm-api:8000/query
INCOMING_ARTICLES_QUEUE=incoming_articles_queue
```

### 2. 템플릿 파일 사용

`env.template` 파일을 참고하여 `.env` 파일을 생성할 수 있습니다:

```bash
cp env.template .env
# .env 파일을 편집하여 실제 API 키들을 입력하세요
```

### 3. 보안 주의사항

- `.env` 파일은 절대 Git에 커밋하지 마세요
- API 키는 안전하게 관리하고 정기적으로 갱신하세요
- 프로덕션 환경에서는 더욱 엄격한 보안 설정을 적용하세요

---

##  주요 기능

- 뉴스 크롤링 및 전처리
- 뉴스 벡터화 및 Pinecone 저장
- LLM을 활용한 요약 및 기사 재작성
- 사용자의 피드백 기반 개인화 추천

---

##  기술 스택

- Python
- LangChain
- Pinecone (Vector DB)
- OpenAI API 또는 로컬 LLM

- React
etc...
  

---

## 🗂 폴더 구조 
```
AIGEN_SCIENCE/
├── README.md
├── .gitignore
├── requirements.txt                # pip 의존성 목록
├── .env                           # 환경 변수 (Git에서 제외됨)
├── env.template                   # 환경 변수 템플릿
├── config/                         # 설정 파일들 (예: API 키, 모델 경로 등)
│   └── config.yaml
├── data/                           # 수집된 원본 데이터, 임베딩된 벡터 등
│   ├── raw/                        # 원시 뉴스 (news_collector)
│   ├── celery_pipeline_logs/       # Celery 파이프라인 단계별 로그 및 데이터
│   │   ├── stage1_initial_checks_celery/
│   │   │   ├── passed/
│   │   │   └── dropped/
│   │   ├── stage2_content_extraction_celery/
│   │   │   ├── passed/
│   │   │   └── failed/
│   │   ├── stage3_categorization_celery/
│   │   │   ├── passed/
│   │   │   └── skipped_or_failed/
│   │   ├── stage4_content_analysis_celery/
│   │   │   ├── passed/
│   │   │   └── dropped/
│   │   ├── stage5_embedding_celery/
│   │   │   ├── passed/
│   │   │   └── failed_or_skipped/
│   │   └── stage6_finalization_celery/
│   │       ├── saved_to_main/
│   │       └── blacklisted/
│   └── embeddings/                 # 최종 임베딩된 데이터
├── src/                            # 핵심 소스 코드
│   ├── __init__.py
│   ├── celery_app.py               # Celery 애플리케이션 정의 및 리소스 초기화
│   ├── config_loader/              # 설정 및 Redis 클라이언트 로더
│   │   └── settings.py
│   │   └── redis.py
│   ├── db/                         # 데이터베이스 인터페이스 (MongoDB, Pinecone)
│   │   ├── mongo_db.py             # MongoDB 관련 로직 (필요시 분리)
│   │   └── vector_db.py            # Pinecone 관련 로직
│   ├── news_collector/             # 뉴스 및 공시 데이터 수집기
│   │   └── news_collector.py
│   │   └── sources/                # 뉴스 수집 소스 목록
│   │       ├── api_sources.txt
│   │       └── rss_sources.txt
│   ├── pipeline_stages/            # Celery 파이프라인의 각 단계 (원자적 태스크)
│   │   ├── __init__.py
│   │   ├── initial_checks.py       # 1단계: 초기 유효성 및 중복 검사
│   │   ├── content_extraction.py   # 2단계: 기사 본문 추출 및 LLM 요약
│   │   ├── categorization.py       # 3단계: LLM 기반 기사 분류 및 키워드 추출
│   │   ├── content_analysis.py     # 4단계: 기사 품질 분석 (불용어, 유해 URL 등)
│   │   ├── embedding_generator.py  # 5단계: 텍스트 임베딩 생성
│   │   └── finalization.py         # 6단계: 최종 DB 저장 및 Pinecone 업서트
│   ├── rag_graph/                  # RAG(Retrieval-Augmented Generation) 워크플로우 정의 (LangGraph)
│   │   └── graph_rag.py
│   ├── query_worker/               # RAG 쿼리 처리 API (FastAPI)
│   │   └── query_worker.py
│   ├── news_recommendation/        # 뉴스 추천 API (FastAPI)
│   │   └── news_recommendation.py
│   ├── news_article/               # 단일 뉴스 기사 조회 API (FastAPI)
│   │   └── news_article_api.py
│   └── common/                     # 공통 유틸리티 함수 
│       └── utils.py                # (예: 날짜/시간 처리, 문자열 정리 등 범용 함수)
├── frontend/                       # 웹 프론트엔드 코드 (React 등)
├── tests/                          # 유닛 및 통합 테스트
│   ├── test_news_collector.py
│   ├── test_initial_checks.py      
│   ├── test_content_extraction.py  
│   ├── test_categorization.py     
│   ├── test_content_analysis.py    
│   ├── test_embedding_generator.py 
│   ├── test_finalization.py
│   ├── test_query_worker.py
│   └── test_news_recommendation.py
├── scripts/                        # 초기화, 일괄 작업, 데이터 마이그레이션 스크립트
│   └── update_embeddings.py        
│   └── run_celery_worker.sh        
└── notebooks/                      # 실험용 Jupyter 노트북
    └── exploratory_analysis.ipynb
└── main.py                         # 전체 애플리케이션 진입점 (FastAPI 서버 또는 스케줄러)
```

## 📊 워크플로우 다이어그램

```
사용자 쿼리
    ↓
대화 기록 조회
    ↓
쿼리 분석 및 재구성
    ↓
고급 검색 (Dense Retrieval + Reranking)
    ├── Dense retrieval로 top 5개 검색
    └── Qwen3-Reranker로 재순위화 → top 3개 선택
    ↓
RAG 답변 생성
    ↓
LLM 기반 정보 충족도 분석 (gpt-4.1-nano)
    ├── 완전성, 구체성, 최신성, 정확성, 유용성 평가
    └── SUFFICIENT/INSUFFICIENT 판단
    ↓
[정보 충분] → 최종 답변 결정 → 대화 저장 → 종료
    ↓ [정보 부족]
웹검색 쿼리 준비
    ↓
웹검색 수행
    ↓
웹검색 답변 생성
    ↓
최종 답변 결정
    ↓
대화 저장
    ↓
종료
```

### 쿼리 처리 워크플로우
1. **쿼리 분석 및 재구성**: 사용자 질문을 분석하고 대화 맥락을 고려하여 재구성
2. **고급 검색**: 500+50 chunking, Dense retrieval + Qwen3-Reranker로 정확한 문서 검색
3. **RAG 답변 생성**: 벡터 DB에서 관련 문서를 검색하여 답변 생성
4. **LLM 기반 정보 충족도 분석**: gpt-4.1-nano가 답변의 완전성, 구체성, 최신성, 정확성, 유용성을 평가
5. **웹검색 수행**: 정보가 부족할 경우 웹검색을 통해 최신 정보 수집
6. **최종 답변 통합**: RAG 또는 웹검색 결과 중 더 적절한 답변 선택

### LLM 기반 정보 충족도 분석
- **gpt-4.1-nano 활용**: 정교한 정보 품질 평가
- **5가지 평가 기준**: 완전성, 구체성, 최신성, 정확성, 유용성
- **지능형 판단**: 단순 키워드 매칭이 아닌 맥락 이해 기반 평가
- **Fallback 시스템**: LLM 오류시 기본 키워드 기반 분석으로 대체

### 웹검색 기능
- **다중 소스 검색**: Google, DuckDuckGo, Wikipedia 등에서 정보 수집
- **품질 기반 필터링**: 중복 제거 및 관련성 높은 결과 우선 선택
- **gpt-4.1-nano 활용**: 웹검색 결과를 바탕으로 정확한 답변 생성

### 고급 검색 시스템
- **500+50 Chunking**: 문맥을 유지하면서 적절한 크기로 텍스트 분할
- **Dense Retrieval**: 벡터 유사도 기반으로 top 5개 문서 검색
- **Qwen3-Reranker**: 재순위화를 통해 top 3개 최적 문서 선택

### config.yaml 설정 항목
- `OPENAI_API_KEY`: OpenAI API 키 (환경 변수에서 로드)
- `OPENAI_RAG_MODEL`: RAG 답변 생성용 모델 (기본값: gpt-4.1-nano)
- `OPENAI_WEB_SEARCH_MODEL`: 웹검색 답변 생성용 모델 (기본값: gpt-4.1-nano)
- `OPENAI_ANALYSIS_MODEL`: 정보 충족도 분석용 모델 (기본값: gpt-4.1-nano)
- `PINECONE_API_KEY`: Pinecone API 키 (환경 변수에서 로드)
- `SHARED_EMBEDDING_MODEL_NAME`: 임베딩 모델명
- `RERANKER_MODEL_NAME`: Reranker 모델명 (기본값: Qwen/Qwen3-Reranker-0.6B)
- `RERANKER_TOP_K`: Reranker 선택 문서 수 (기본값: 3)
- `DENSE_RETRIEVAL_TOP_K`: Dense retrieval 검색 문서 수 (기본값: 5)