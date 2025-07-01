# PDF 프로세서 사용 가이드

이 프로젝트는 PDF 파일을 업로드하고 GPT로 분석하여 MongoDB와 Pinecone DB에 저장하는 시스템입니다.

## 🚀 주요 기능

- **PDF 텍스트 추출**: PyPDF2를 사용한 PDF 텍스트 추출
- **GPT 분석**: 제목, 요약, 키워드, 카테고리, 중요도 자동 분석
- **텍스트 청킹**: LangChain을 사용한 텍스트 분할
- **벡터 임베딩**: OpenAI 임베딩 모델을 사용한 벡터 생성
- **MongoDB 저장**: 문서 데이터 저장
- **Pinecone 저장**: 벡터 데이터 저장 및 유사도 검색
- **REST API**: FastAPI를 사용한 웹 API 제공

## 📋 사전 요구사항

### 1. 설정 파일 준비

`config/config.yaml` 파일을 생성하고 다음 설정을 추가하세요:

```yaml
# OpenAI 설정
OPENAI_API_KEY: "your-openai-api-key"
OPENAI_LLM_EXTRACTION_MODEL: "gpt-4.1-nano"
SHARED_EMBEDDING_MODEL_NAME: "text-embedding-3-small"

# MongoDB 설정
MONGO_URI: "mongodb+srv://username:password@host/database"
MONGO_DB_NAME: "newsdb"
MONGO_ARTICLES_COLLECTION_NAME: "articles"

# Pinecone 설정
PINECONE_API_KEY: "your-pinecone-api-key"
PINECONE_INDEX_NAME: "your-index-name"
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

## 🛠️ 설치 및 실행

### 1. PDF API 서버 실행

```bash
python src/api/pdf_api.py
```

서버가 `http://localhost:8001`에서 실행됩니다.

### 2. API 문서 확인

브라우저에서 `http://localhost:8001/docs`에 접속하여 Swagger UI를 통해 API를 테스트할 수 있습니다.

## 📚 API 엔드포인트

### 1. PDF 업로드

**단일 파일 업로드**
```bash
curl -X POST "http://localhost:8001/upload-pdf" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_document.pdf"
```

**일괄 업로드**
```bash
curl -X POST "http://localhost:8001/upload-pdf-batch" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@file1.pdf" \
  -F "files=@file2.pdf"
```

### 2. PDF 목록 조회

```bash
curl -X GET "http://localhost:8001/list-pdfs?skip=0&limit=20&category=기술"
```

### 3. PDF 검색

```bash
curl -X GET "http://localhost:8001/search-pdfs?query=인공지능&limit=10"
```

### 4. PDF 상세 정보 조회

```bash
curl -X GET "http://localhost:8001/pdf/{pdf_id}"
```

### 5. PDF 삭제

```bash
curl -X DELETE "http://localhost:8001/pdf/{pdf_id}"
```

### 6. 헬스 체크

```bash
curl -X GET "http://localhost:8001/health"
```

## 🧪 테스트

### 1. 통합 테스트 실행

```bash
python test_pdf_processor.py
```

이 스크립트는 다음을 수행합니다:
- 테스트 PDF 파일 생성
- API 서버 연결 확인
- PDF 업로드 테스트
- 검색 기능 테스트

### 2. 수동 테스트

```python
from src.pdf_processor import PDFProcessor

# PDF 프로세서 초기화
processor = PDFProcessor()

# PDF 파일 읽기
with open("test.pdf", "rb") as f:
    pdf_content = f.read()

# PDF 처리
result = processor.process_pdf(pdf_content, "test.pdf")
print(result)
```

## 📊 데이터 구조

### MongoDB 저장 필드

```json
{
  "ID": "uuid-string",
  "checked": {
    "pdf_processed": true,
    "processed_at": "2024-01-01T00:00:00",
    "processing_status": "completed"
  },
  "content": "전체 텍스트 내용",
  "embedding": [0.1, 0.2, ...],
  "llm_individual_keyword_embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]],
  "llm_internal_keywords": ["키워드1", "키워드2"],
  "llm_internal_keywords_embedding": [0.1, 0.2, ...],
  "published_at": "2024-01-01T00:00:00",
  "source": "pdf_upload",
  "summary": "문서 요약",
  "title": "문서 제목"
}
```

### Pinecone 저장 필드

```json
{
  "id": "uuid-string",
  "content": "내용 일부",
  "llm_internal_keywords": "키워드1, 키워드2",
  "published_at": "2024-01-01T00:00:00",
  "source": "pdf_upload",
  "summary": "문서 요약",
  "title": "문서 제목"
}
```

## 🔧 설정 옵션

### PDF 처리 설정

- **청크 크기**: 기본 1000자 (조정 가능)
- **청크 오버랩**: 기본 200자 (조정 가능)
- **파일 크기 제한**: 50MB
- **지원 형식**: PDF만

### GPT 분석 설정

- **모델**: gpt-4.1-nano (기본값)
- **온도**: 0.3 (일관성 있는 결과)
- **최대 토큰**: 500

### 임베딩 설정

- **모델**: text-embedding-3-small (기본값)
- **벡터 크기**: 1536차원

## 🚨 주의사항

1. **API 키 보안**: OpenAI와 Pinecone API 키를 안전하게 관리하세요
2. **파일 크기**: 대용량 PDF 파일은 처리 시간이 오래 걸릴 수 있습니다
3. **중복 체크**: 동일한 PDF 파일은 해시 기반으로 중복 체크됩니다
4. **메모리 사용**: 대용량 파일 처리 시 충분한 메모리를 확보하세요

## 🐛 문제 해결

### 일반적인 오류

1. **MongoDB 연결 실패**
   - MongoDB URI 확인
   - 네트워크 연결 상태 확인

2. **Pinecone 연결 실패**
   - API 키 확인
   - 인덱스 이름 확인

3. **OpenAI API 오류**
   - API 키 확인
   - 사용량 한도 확인

4. **PDF 텍스트 추출 실패**
   - PDF 파일이 손상되지 않았는지 확인
   - 스캔된 PDF는 텍스트 추출이 어려울 수 있음

### 로그 확인

서버 실행 시 상세한 로그가 출력됩니다. 오류 발생 시 로그를 확인하여 문제를 파악하세요.

## 📈 성능 최적화

1. **청크 크기 조정**: 문서 특성에 맞게 청크 크기 조정
2. **배치 처리**: 여러 파일을 한 번에 업로드하여 효율성 향상
3. **캐싱**: 자주 사용되는 임베딩 결과 캐싱
4. **비동기 처리**: 대용량 파일은 백그라운드에서 처리

## 🤝 기여하기

버그 리포트나 기능 제안은 이슈를 통해 제출해주세요.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 