# src/celery_app.py
from datetime import datetime
import os
import sys
from celery import Celery
from celery.signals import worker_process_shutdown
from celery.schedules import crontab # Celery Beat 스케줄을 위해 추가
import json
import traceback

# 프로젝트 루트 설정
_current_file_path = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(_current_file_path))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
print(f"[{datetime.now()}] Project root configured: {_project_root}")

# SETTINGS 임포트 추가
from src.config_loader.settings import SETTINGS

# news_collector 모듈 임포트 제거 (순환 참조 방지)
# try:
#     from src.news_collector import news_collector
#     print(f"[{datetime.now()}] news_collector module imported successfully.")
# except ImportError as e:
#     print(f"[{datetime.now()}] ERROR: Failed to import news_collector module: {e}")
#     sys.exit(1) # 모듈 임포트 실패 시 종료

# pipeline_stages 모듈 import (Celery task 등록을 위해)
# 이 부분은 삭제 - initial_checks.py에서 직접 태스크를 정의하므로 불필요

# 필요한 클라이언트 클래스 임포트 (기존 코드에서 가져옴)
from pymongo import MongoClient
import certifi
from src.db.vector_db import PineconeDB
from openai import OpenAI

print(f"[{datetime.now()}] All top-level imports in celery_app.py have been completed.")

# --- 전역 리소스 초기화 ---
worker_resources = {}
initialization_errors = []

print(f"[{datetime.now()}] Attempting GLOBAL (module-level) resource initialization.")

try:
    # MongoDB 초기화
    # SETTINGS에서 MONGO_URI를 읽어옵니다.
    mongo_uri = SETTINGS.get('MONGO_URI')
    if not mongo_uri:
        raise ValueError("MONGO_URI not set in config.yaml or environment variables.")
    
    # SSL/TLS 설정은 MongoDB URI에 포함될 수도 있고, certifi가 사용될 수도 있습니다.
    # 여기서는 certifi를 사용하여 CA 인증서를 지정하는 일반적인 방법을 보여줍니다.
    mongo_client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
    # MongoDB 연결 테스트 (필요한 경우)
    mongo_client.admin.command('ping') 
    worker_resources['mongo_client'] = mongo_client
    
    # MongoDB 컬렉션들 초기화
    mongo_db_name = SETTINGS.get('MONGO_DB_NAME', 'newsdb')
    mongo_articles_collection_name = SETTINGS.get('MONGO_ARTICLES_COLLECTION_NAME', 'articles')
    mongo_blacklist_collection_name = SETTINGS.get('MONGO_BLACKLIST_COLLECTION_NAME', 'Filter3')
    
    mongo_db = mongo_client[mongo_db_name]
    articles_collection = mongo_db[mongo_articles_collection_name]
    blacklist_collection = mongo_db[mongo_blacklist_collection_name]
    
    worker_resources['articles_collection'] = articles_collection
    worker_resources['blacklist_collection'] = blacklist_collection
    
    print(f"[{datetime.now()}] MongoDB client initialized successfully.")
    print(f"[{datetime.now()}] MongoDB collections initialized: {mongo_articles_collection_name}, {mongo_blacklist_collection_name}")

    # PineconeDB 초기화
    # SETTINGS에서 Pinecone 설정을 읽어옵니다.
    pinecone_api_key = SETTINGS.get('PINECONE_API_KEY')
    pinecone_environment = SETTINGS.get('PINECONE_ENVIRONMENT', 'us-east-1')
    pinecone_index_name = SETTINGS.get('PINECONE_INDEX_NAME', 'news-embedding-3')
    
    if not pinecone_api_key:
        raise ValueError("PINECONE_API_KEY not set in config.yaml or environment variables.")

    pinecone_db = PineconeDB()
    worker_resources['pinecone_manager'] = pinecone_db
    print(f"[{datetime.now()}] PineconeDB client initialized successfully.")

    # OpenAI 클라이언트 초기화
    # SETTINGS에서 OPENAI_API_KEY를 읽어옵니다.
    openai_api_key = SETTINGS.get('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not set in config.yaml or environment variables.")
    
    openai_client = OpenAI(api_key=openai_api_key)
    worker_resources['openai_client'] = openai_client
    print(f"[{datetime.now()}] OpenAI client initialized successfully.")

    # 다른 API 키들도 SETTINGS에서 가져와서 필요한 곳에 전달하거나 전역으로 설정할 수 있습니다.
    worker_resources['DART_API_KEY'] = SETTINGS.get('DART_API_KEY')
    worker_resources['NAVER_CLIENT_ID'] = SETTINGS.get('NAVER_CLIENT_ID')
    worker_resources['NAVER_CLIENT_SECRET'] = SETTINGS.get('NAVER_CLIENT_SECRET')
    
    # 모델명들 추가
    worker_resources['embedding_model_name'] = SETTINGS.get('SHARED_EMBEDDING_MODEL_NAME', 'text-embedding-3-small')

except Exception as e:
    initialization_errors.append(f"Global resource initialization failed: {e}\n{traceback.format_exc()}")
    print(f"[{datetime.now()}] CRITICAL ERROR during global resource initialization: {e}")
    print(traceback.format_exc()) # 스택 트레이스 출력

# Celery 앱 인스턴스 생성
# SETTINGS에서 CELERY_BROKER_URL과 CELERY_RESULT_BACKEND를 가져옵니다.
app = Celery('aigen_science',
             broker=SETTINGS.get('CELERY_BROKER_URL', 'redis://redis:6379/0'),
             backend=SETTINGS.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'))

# Celery Beat 스케줄 설정 (여기가 핵심 변경 사항 중 하나)
app.conf.beat_schedule = {
    'run-news-collector-every-hour': {
        'task': 'src.celery_app.collect_news_task', # 아래에 정의할 태스크의 이름
        'schedule': crontab(minute=0, hour='0,12'),
        'args': (), # 태스크에 전달할 인수가 있다면 여기에 튜플로 넣습니다.
        'options': {'queue': 'default'} # 필요에 따라 큐 지정
    },
    # 여기에 다른 주기적인 Celery Beat 태스크를 추가할 수 있습니다.
}
app.conf.timezone = 'Asia/Seoul' # 시간대 설정 (한국 시간으로 매 시간 0분)
print(f"[{datetime.now()}] Celery app configured with Beat schedule. Timezone: {app.conf.timezone}")

# Celery 앱 인스턴스를 celery_app으로도 접근할 수 있도록 별칭 추가
celery_app = app

# initial_checks 모듈 import (태스크 등록을 위해)
import src.pipeline_stages.initial_checks
import src.pipeline_stages.initial_checks
import src.pipeline_stages.content_extraction
import src.pipeline_stages.categorization
import src.pipeline_stages.content_analysis
import src.pipeline_stages.embedding_generator
import src.pipeline_stages.finalization
# --- Celery 태스크 정의 ---

# 뉴스 수집 태스크 (news_collector.py의 main 함수 호출)
@app.task
def collect_news_task():
    """
    주기적으로 뉴스 데이터를 수집하는 Celery 태스크.
    news_collector.py의 main 함수를 호출합니다.
    """
    if initialization_errors:
        print(f"[{datetime.now()}] 뉴스 수집 태스크: 전역 리소스 초기화 오류로 인해 실행되지 않습니다.")
        for error in initialization_errors:
            print(error)
        return
        
    print(f"[{datetime.now()}] 뉴스 수집 태스크 시작...")
    try:
        # Lazy import로 순환 참조 방지
        from src.news_collector import news_collector
        # news_collector.py의 main 함수를 호출합니다.
        # news_collector.main() 함수가 제대로 정의되어 있고,
        # 이 함수 내에서 필요한 모든 환경 변수(DART, NAVER 등)를 SETTINGS에서 읽도록 되어 있어야 합니다.
        news_collector.collect_all_data() 
        print(f"[{datetime.now()}] 뉴스 수집 태스크 완료.")
    except Exception as e:
        print(f"[{datetime.now()}] ERROR: 뉴스 수집 태스크 오류 발생: {e}")
        print(traceback.format_exc()) # 상세 오류 로그 출력

# PDF 처리 태스크 (예시)
@app.task
def process_pdf_task(file_path):
    """
    PDF 파일을 처리하는 Celery 태스크 (예시).
    """
    if initialization_errors:
        print(f"[{datetime.now()}] PDF 처리 태스크: 전역 리소스 초기화 오류로 인해 실행되지 않습니다.")
        for error in initialization_errors:
            print(error)
        return

    print(f"[{datetime.now()}] PDF 처리 태스크 시작: {file_path}")
    try:
        # 여기에 PDF 처리 로직을 구현합니다.
        # 필요한 리소스(예: worker_resources['openai_client'])를 여기서 사용합니다.
        # 예: result = some_pdf_processing_function(file_path, openai_client=worker_resources['openai_client'])
        print(f"[{datetime.now()}] PDF 처리 태스크 완료: {file_path}")
        return {"status": "success", "file": file_path}
    except Exception as e:
        print(f"[{datetime.now()}] ERROR: PDF 처리 태스크 오류 발생: {e}")
        print(traceback.format_exc())
        return {"status": "failed", "file": file_path, "error": str(e)}

# Celery Worker 프로세스 종료 시 리소스 정리
@worker_process_shutdown.connect
def cleanup_worker_resources(sender=None, **kwargs):
    print(f"[{datetime.now()}] Celery worker shutting down. Cleaning up resources...")
    if 'mongo_client' in worker_resources and worker_resources['mongo_client']:
        worker_resources['mongo_client'].close()
        print(f"[{datetime.now()}] MongoDB client closed.")
    # PineconeDB는 명시적인 close 메서드가 없을 수 있습니다.
    # 필요한 다른 리소스 정리 로직을 여기에 추가합니다.
    print(f"[{datetime.now()}] Resource cleanup complete.")

# --- 유틸리티 함수 (기존 코드에서 가져옴) ---

# 이 함수는 Celery 태스크 내에서 직접 사용되지 않을 수 있지만,
# 프로젝트의 다른 부분에서 필요할 수 있으므로 유지합니다.
def save_to_data_folder(article_data, stage_name_path, status_prefix="processed"):
    return # 이 함수는 현재 return으로 바로 종료되므로 실제 저장 기능은 없습니다.
    log_dir_base = os.path.join(_project_root, "data", "celery_pipeline_logs")
    log_dir_stage = os.path.join(log_dir_base, stage_name_path)
    os.makedirs(log_dir_stage, exist_ok=True)

    filename_safe_title = "".join(c if c.isalnum() else "_" for c in article_data.get("title", "no_title"))[:50]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    unique_id_part = article_data.get("id", "no_id")
    if unique_id_part == "no_id" and article_data.get("url"):
        unique_id_part = "".join(c if c.isalnum() else "_" for c in article_data.get("url"))[-20:]

    filename = f"{status_prefix}_{filename_safe_title}_{timestamp}_{unique_id_part}.json"
    filepath = os.path.join(log_dir_stage, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            # MongoDB ObjectId와 같은 직렬화 불가능한 객체들을 처리
            def convert_sets_to_lists(obj):
                if isinstance(obj, set):
                    return list(obj)
                elif isinstance(obj, dict):
                    return {k: convert_sets_to_lists(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_sets_to_lists(item) for item in obj]
                else:
                    return obj
            
            converted_data = convert_sets_to_lists(article_data)
            json.dump(converted_data, f, ensure_ascii=False, indent=2, default=str)
        print(f"  📁 Celery Pipeline Log: {filepath}")
        return filepath
    except Exception as e:
        print(f"  ❌ Celery Pipeline Log 저장 실패: {e}")
        return None
