# aigen-science_RAG

#  AIGEN Science

AI 기반 정보 수집, 요약, 개인화 시스템 개발 프로젝트입니다.  
LLM과 RAG(Retrieval-Augmented Generation) 구조를 활용하여 사용자가 원하는 정보를 빠르게 가공하고 전달하는 것을 목표로 합니다.

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
- (백엔드 예정)
- (프론트 예정)
  

---

## 🗂 폴더 구조 (예정)
news-ai-project-template/
├── app/
│   ├── api/              # API 라우터
│   ├── services/         # 수집, 필터링, 요약 등 로직
│   ├── workers/          # Celery 태스크
│   ├── models/           # models
│   ├── db/               # MongoDB, vectorDB 연결 및 함수
│   └── core/             # 설정, 유틸리티
│
├── tests/                # 테스트 코드
├── .env.example          # 환경변수 템플릿(API 키들 여기에 저장?)
├── .gitignore            # 기본 Git 무시 설정
├── docker-compose.yml    # Redis, MongoDB, FastAPI 포함 실행
├── requirements.txt      # 버전, 필요한 패키지들
├── README.md             # 프로젝트 설명
└── main.py               # main.py

