# Docker 최적화 구조

## 문제점
기존에는 모든 서비스가 동일한 `Dockerfile`과 `requirements.txt`를 사용하여 torch, transformers, scikit-learn, streamlit, huggingface_hub 등 무거운 라이브러리들이 모든 컨테이너에 설치되었습니다.

## 해결책
서비스별로 필요한 패키지만 설치하는 최적화된 Dockerfile 구조로 변경했습니다.

## 새로운 구조

### 1. 공통 패키지 (requirements-base.txt)
모든 서비스에서 공통으로 사용되는 기본 패키지들:
- HTTP/웹 관련: requests, beautifulsoup4, lxml
- 데이터베이스: redis, pymongo, pinecone-client, supabase
- 웹 프레임워크: fastapi, uvicorn
- 비동기 처리: celery, eventlet
- 기타: pandas, numpy, pyyaml 등

### 2. 서비스별 전용 패키지

#### LLM API (Dockerfile.llm + requirements-llm.txt)
- OpenAI 및 LangChain 관련 패키지
- LangGraph

#### RAG API (Dockerfile.rag + requirements-rag.txt)
- 머신러닝: scikit-learn, transformers, torch, nltk
- OpenAI 및 LangChain 관련 패키지
- LangGraph

#### PDF API (Dockerfile.pdf + requirements-pdf.txt)
- PDF 처리: PyPDF2, reportlab

#### 웹 인터페이스 (Dockerfile.web + requirements-web.txt)
- Streamlit
- Plotly

#### 뉴스 서비스 (Dockerfile.news)
- 기본 패키지만 사용 (추가 패키지 불필요)

#### Celery 워커 (Dockerfile.celery)
- 기본 패키지만 사용 (추가 패키지 불필요)

## 사용법

### 기존 빌드 정리
```bash
# 기존 이미지 및 컨테이너 정리
docker-compose down
docker system prune -a
```

### 새로운 구조로 빌드
```bash
# 최적화된 구조로 빌드
docker-compose build

# 또는 특정 서비스만 빌드
docker-compose build llm-api
docker-compose build rag-api
docker-compose build pdf-api
```

### 서비스 실행
```bash
# 전체 서비스 실행
docker-compose up -d

# 특정 서비스만 실행
docker-compose up -d llm-api rag-api
```

## 장점

1. **이미지 크기 감소**: 각 서비스가 필요한 패키지만 포함
2. **빌드 시간 단축**: 불필요한 패키지 설치 시간 제거
3. **보안 향상**: 불필요한 패키지로 인한 보안 취약점 감소
4. **리소스 효율성**: 메모리 및 디스크 사용량 최적화

## 이미지 크기 비교

### 기존 (모든 패키지 포함)
- 각 컨테이너: ~2-3GB

### 최적화 후
- LLM API: ~500MB
- RAG API: ~1.5GB (torch, transformers 포함)
- PDF API: ~300MB
- 뉴스 서비스: ~400MB
- Celery 워커: ~400MB

## 주의사항

1. 기존 `requirements.txt`는 `requirements.txt.backup`으로 백업되었습니다.
2. 새로운 구조로 전환 시 기존 이미지를 모두 삭제하고 재빌드해야 합니다.
3. 각 서비스의 의존성이 변경될 경우 해당 requirements 파일을 업데이트해야 합니다.

## 문제 해결

### 특정 서비스에서 패키지 누락 오류 발생 시
해당 서비스의 requirements 파일에 누락된 패키지를 추가하세요.

### 기존 구조로 되돌리기
```bash
mv requirements.txt.backup requirements.txt
# docker-compose.yml에서 모든 dockerfile을 원래 Dockerfile로 변경
``` 