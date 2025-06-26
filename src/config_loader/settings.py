# src/config_loader/settings.py
import os
import yaml
from datetime import datetime
from dotenv import load_dotenv

print(f"[{datetime.now()}] Loading settings from src/config_loader/settings.py...")

# .env 파일 로드
_current_file_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_current_file_dir, '..', '..'))
env_path = os.path.join(_project_root, '.env')

# .env 파일이 존재하면 로드
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"[{datetime.now()}] .env loaded successfully from: {env_path}")
else:
    print(f"[{datetime.now()}] WARNING: .env not found at {env_path}")

# 프로젝트의 루트 디렉토리를 찾아 config.yaml 파일의 절대 경로를 만듭니다.
# 현재 파일 (settings.py)의 디렉토리에서 두 단계 위로 올라가면 프로젝트 루트입니다.
# src/config_loader/settings.py -> src/config_loader -> src -> Aigen_science (Project Root)
config_yaml_path = os.path.join(_project_root, 'config', 'config.yaml')

CONFIG = {} # config.yaml에서 로드될 설정을 저장할 딕셔너리

try:
    with open(config_yaml_path, 'r', encoding='utf-8') as f:
        CONFIG = yaml.safe_load(f)
    print(f"[{datetime.now()}] config.yaml loaded successfully from: {config_yaml_path}")
except FileNotFoundError:
    print(f"[{datetime.now()}] WARNING: config.yaml not found at {config_yaml_path}. Proceeding with environment variables and defaults.")
except yaml.YAMLError as e:
    print(f"[{datetime.now()}] ERROR: Failed to parse config.yaml: {e}. Check YAML syntax.")
    CONFIG = {} # YAML 파싱 실패 시 빈 딕셔너리로 초기화

# --- 환경 변수와 config.yaml 값을 통합하여 최종 설정 정의 ---
# os.environ.get()을 사용하여 환경 변수에서 먼저 값을 가져오고,
# 환경 변수가 없으면 config.yaml에서 읽어온 값을 사용하도록 합니다.
# config.yaml에도 없다면 None을 반환하거나 적절한 기본값을 설정할 수 있습니다.

# MongoDB 설정
MONGO_URI = os.environ.get('MONGO_URI', CONFIG.get('MONGO_URI'))
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', CONFIG.get('MONGO_DB_NAME', 'newsdb'))
MONGO_ARTICLES_COLLECTION_NAME = os.environ.get('MONGO_ARTICLES_COLLECTION_NAME', CONFIG.get('MONGO_ARTICLES_COLLECTION_NAME', 'articles'))
MONGO_BLACKLIST_COLLECTION_NAME = os.environ.get('MONGO_BLACKLIST_COLLECTION_NAME', CONFIG.get('MONGO_BLACKLIST_COLLECTION_NAME', 'Filter3'))

# Redis 설정
REDIS_HOST = os.environ.get('REDIS_HOST', CONFIG.get('REDIS_HOST', 'redis'))
REDIS_PORT = int(os.environ.get('REDIS_PORT', CONFIG.get('REDIS_PORT', 6379))) # 숫자로 형변환
REDIS_DB = int(os.environ.get('REDIS_DB', CONFIG.get('REDIS_DB', 0))) # 숫자로 형변환
REDIS_BLOCK_TIMEOUT = int(os.environ.get('REDIS_BLOCK_TIMEOUT', CONFIG.get('REDIS_BLOCK_TIMEOUT', 30))) # 숫자로 형변환

# API 키 및 기타 민감 정보 - .env에서 우선적으로 로드
DART_API_KEY = os.environ.get('DART_API_KEY', CONFIG.get('DART_API_KEY'))
NAVER_CLIENT_ID = os.environ.get('NAVER_CLIENT_ID', CONFIG.get('NAVER_CLIENT_ID'))
NAVER_CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET', CONFIG.get('NAVER_CLIENT_SECRET'))
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', CONFIG.get('OPENAI_API_KEY'))
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY', CONFIG.get('PINECONE_API_KEY'))

# Pinecone 환경 정보
PINECONE_ENVIRONMENT = os.environ.get('PINECONE_ENVIRONMENT', CONFIG.get('PINECONE_ENVIRONMENT', 'us-east-1'))
PINECONE_INDEX_NAME = os.environ.get('PINECONE_INDEX_NAME', CONFIG.get('PINECONE_INDEX_NAME', 'news-embedding-3'))

# 기타 모델 및 경로 설정 (config.yaml에만 있을 것으로 가정)
OPENAI_MODEL_NAME = CONFIG.get('OPENAI_MODEL_NAME', 'gpt-4.1-nano')
OPENAI_RAG_MODEL = CONFIG.get('OPENAI_RAG_MODEL', 'gpt-4.1-nano')
OPENAI_WEB_SEARCH_MODEL = CONFIG.get('OPENAI_WEB_SEARCH_MODEL', 'gpt-4.1-mini')
OPENAI_ANALYSIS_MODEL = CONFIG.get('OPENAI_ANALYSIS_MODEL', 'gpt-4.1-nano')
OPENAI_KEYWORD_MODEL = CONFIG.get('OPENAI_KEYWORD_MODEL', 'gpt-4.1-nano')
OPENAI_LLM_EXTRACTION_MODEL = CONFIG.get('OPENAI_LLM_EXTRACTION_MODEL', 'gpt-4.1-nano')
OPENAI_LLM_SUMMARY_MODEL = CONFIG.get('OPENAI_LLM_SUMMARY_MODEL', 'gpt-4.1-nano')
SHARED_EMBEDDING_MODEL_NAME = CONFIG.get('SHARED_EMBEDDING_MODEL_NAME', 'text-embedding-3-small')
RERANKER_MODEL_NAME = CONFIG.get('RERANKER_MODEL_NAME', 'Qwen/Qwen3-Reranker-0.6B')
RERANKER_TOP_K = CONFIG.get('RERANKER_TOP_K', 5)
DENSE_RETRIEVAL_TOP_K = CONFIG.get('DENSE_RETRIEVAL_TOP_K', 10)
RAG_NUM_RETRIEVED_DOCS = CONFIG.get('RAG_NUM_RETRIEVED_DOCS', 3)
RAG_MIN_SIMILARITY_SCORE = CONFIG.get('RAG_MIN_SIMILARITY_SCORE', 0.0)
RAW_DATA_PATH = CONFIG.get('RAW_DATA_PATH', 'data/raw')
FILTER2_MODEL_DIR = CONFIG.get('FILTER2_MODEL_DIR') # 이 경로는 중요하니 None 허용
PINECONE_CONTENT_MAX_LENGTH = CONFIG.get('PINECONE_CONTENT_MAX_LENGTH', 20000)
SIMILARITY_THRESHOLD_CONTENT = CONFIG.get('SIMILARITY_THRESHOLD_CONTENT', 0.91)
CELERY_BROKER_URL = CONFIG.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = CONFIG.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
API_URL = CONFIG.get('API_URL', 'http://llm-api:8000/query')
INCOMING_ARTICLES_QUEUE = CONFIG.get('INCOMING_ARTICLES_QUEUE', 'incoming_articles_queue')

# LLM_CATEGORIZATION 설정
LLM_CATEGORIZATION = CONFIG.get('LLM_CATEGORIZATION', {
    'ENABLED': True,
    'CATEGORIZATION_MODEL': 'gpt-4.1-nano',
    'MAX_CATEGORIES_PER_DIMENSION': 3,
    'MAX_INTERNAL_KEYWORDS': 7,
    'MAX_SUB_CATS_PER_MAIN_CAT': 3,
    'MAX_TOTAL_SUB_CATS_PER_ARTICLE': 9
})

# Supabase 설정
supabase_url = os.environ.get('SUPABASE_URL', CONFIG.get('supabase_url'))
supabase_key = os.environ.get('SUPABASE_KEY', CONFIG.get('supabase_key'))

# API 서버 설정
NEWS_ARTICLES_API_SERVER_HOST = CONFIG.get('NEWS_ARTICLES_API_SERVER_HOST', '0.0.0.0')
NEWS_ARTICLES_API_SERVER_PORT = CONFIG.get('NEWS_ARTICLES_API_SERVER_PORT', 8002)

# 필요한 경우 모든 설정을 한 번에 담는 SETTINGS 딕셔너리 또는 객체 생성
SETTINGS = {
    'MONGO_URI': MONGO_URI,
    'MONGO_DB_NAME': MONGO_DB_NAME,
    'MONGO_ARTICLES_COLLECTION_NAME': MONGO_ARTICLES_COLLECTION_NAME,
    'MONGO_BLACKLIST_COLLECTION_NAME': MONGO_BLACKLIST_COLLECTION_NAME,
    'REDIS_HOST': REDIS_HOST,
    'REDIS_PORT': REDIS_PORT,
    'REDIS_DB': REDIS_DB,
    'REDIS_BLOCK_TIMEOUT': REDIS_BLOCK_TIMEOUT,
    'DART_API_KEY': DART_API_KEY,
    'NAVER_CLIENT_ID': NAVER_CLIENT_ID,
    'NAVER_CLIENT_SECRET': NAVER_CLIENT_SECRET,
    'OPENAI_API_KEY': OPENAI_API_KEY,
    'PINECONE_API_KEY': PINECONE_API_KEY,
    'PINECONE_ENVIRONMENT': PINECONE_ENVIRONMENT,
    'PINECONE_INDEX_NAME': PINECONE_INDEX_NAME,
    'OPENAI_MODEL_NAME': OPENAI_MODEL_NAME,
    'OPENAI_RAG_MODEL': OPENAI_RAG_MODEL,
    'OPENAI_WEB_SEARCH_MODEL': OPENAI_WEB_SEARCH_MODEL,
    'OPENAI_ANALYSIS_MODEL': OPENAI_ANALYSIS_MODEL,
    'OPENAI_KEYWORD_MODEL': OPENAI_KEYWORD_MODEL,
    'OPENAI_LLM_EXTRACTION_MODEL': OPENAI_LLM_EXTRACTION_MODEL,
    'OPENAI_LLM_SUMMARY_MODEL': OPENAI_LLM_SUMMARY_MODEL,
    'SHARED_EMBEDDING_MODEL_NAME': SHARED_EMBEDDING_MODEL_NAME,
    'RERANKER_MODEL_NAME': RERANKER_MODEL_NAME,
    'RERANKER_TOP_K': RERANKER_TOP_K,
    'DENSE_RETRIEVAL_TOP_K': DENSE_RETRIEVAL_TOP_K,
    'RAG_NUM_RETRIEVED_DOCS': RAG_NUM_RETRIEVED_DOCS,
    'RAG_MIN_SIMILARITY_SCORE': RAG_MIN_SIMILARITY_SCORE,
    'RAW_DATA_PATH': RAW_DATA_PATH,
    'FILTER2_MODEL_DIR': FILTER2_MODEL_DIR,
    'PINECONE_CONTENT_MAX_LENGTH': PINECONE_CONTENT_MAX_LENGTH,
    'SIMILARITY_THRESHOLD_CONTENT': SIMILARITY_THRESHOLD_CONTENT,
    'CELERY_BROKER_URL': CELERY_BROKER_URL,
    'CELERY_RESULT_BACKEND': CELERY_RESULT_BACKEND,
    'API_URL': API_URL,
    'INCOMING_ARTICLES_QUEUE': INCOMING_ARTICLES_QUEUE,
    'LLM_CATEGORIZATION': LLM_CATEGORIZATION,
    'supabase_url': supabase_url,
    'supabase_key': supabase_key,
    'NEWS_ARTICLES_API_SERVER_HOST': NEWS_ARTICLES_API_SERVER_HOST,
    'NEWS_ARTICLES_API_SERVER_PORT': NEWS_ARTICLES_API_SERVER_PORT,
}

print(f"[{datetime.now()}] Settings loaded. MONGO_URI preview: {str(SETTINGS.get('MONGO_URI'))[:30]}...")
print(f"[{datetime.now()}] OPENAI_API_KEY loaded: {'****' + SETTINGS.get('OPENAI_API_KEY', '')[-4:] if SETTINGS.get('OPENAI_API_KEY') else 'Not Set'}")
print(f"[{datetime.now()}] DART_API_KEY loaded: {'****' + SETTINGS.get('DART_API_KEY', '')[-4:] if SETTINGS.get('DART_API_KEY') else 'Not Set'}")
