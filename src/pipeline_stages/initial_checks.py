# src/pipeline_stages/initial_checks.py
import os
import json
from datetime import datetime, timedelta, timezone # 'timedelta', 'timezone' 추가
import dateutil.parser  # 'dateutil.parser' 추가
from celery import shared_task
from src.pipeline_stages.content_extraction import content_extraction_task
from src.pipeline_stages.finalization import generate_article_id
from src.pipeline_stages.content_analysis import content_analysis_task
from src.config_loader.settings import SETTINGS

HARDCODED_DROP_URLS = ["google.com/search", "example.org/ads", "m.skyedaily.com", "www.hinews.co.kr", "badsite.com"]

def _save_to_blacklist(article_data: dict, blacklist_db_collection, drop_reason_tag: str):
    if blacklist_db_collection is None:
        print(f"InitialChecks Task Error: 블랙리스트 DB 컬렉션이 제공되지 않아 저장할 수 없습니다: {article_data.get('url')}")
        return
    try:
        article_data.setdefault("checked", {})
        article_data["checked"]["dropped_stage"] = "initial_checks_celery"
        article_data["checked"]["dropped_reason_tag"] = drop_reason_tag
        article_data["checked"]["dropped_at"] = datetime.now().isoformat()

        if "ID" not in article_data or not article_data["ID"]:
            article_data["ID"] = generate_article_id(article_data.get("url"))

        filter_query = {"ID": article_data.get("ID")}
        update_data = {"$set": article_data}
        blacklist_db_collection.update_one(filter_query, update_data, upsert=True)
        print(f"  InitialChecks Task: 기사 '{article_data.get('title', '')[:30]}...' 블랙리스트({drop_reason_tag}) 저장 완료.")
    except Exception as e:
        print(f"  InitialChecks Task Error: 블랙리스트 저장 중 오류: {e} for URL {article_data.get('url')}")

def save_to_data_folder(article_data, stage_name_path, status_prefix="processed"):
    """데이터 폴더에 저장하는 유틸리티 함수"""
    return  # 현재는 비활성화
    log_dir_base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "celery_pipeline_logs")
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

@shared_task(
    name="src.pipeline_stages.initial_checks.initial_checks_task",
    bind=True, max_retries=3, default_retry_delay=60
)
def initial_checks_task(self, article_data: dict):
    """Celery task for initial article checks."""
    task_id_log = f"(Task ID: {self.request.id})" if self.request.id else ""
    print(f"\n📰 Initial Checks Task: 새 기사 처리 시작 {task_id_log} - {article_data.get('url', 'URL 없음')[:70]}...")
    current_stage_name_path = "stage1_initial_checks_celery"

    # 필요할 때만 가져오기
    import src.celery_app
    worker_resources = src.celery_app.worker_resources
    save_to_data_folder = src.celery_app.save_to_data_folder

    articles_collection = worker_resources.get('articles_collection')
    blacklist_collection = worker_resources.get('blacklist_collection')

    if articles_collection is None or blacklist_collection is None:
        error_msg = f"DB 컬렉션 초기화 안됨. articles_collection is None: {articles_collection is None}, blacklist_collection is None: {blacklist_collection is None}"
        print(f"❌ Initial Checks Task CRITICAL: {error_msg} {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/error_db_init", "error")
        raise Exception(f"Initial Checks DB Uninitialized: {error_msg}")

    if "ID" not in article_data or not article_data["ID"]:
        article_data["ID"] = generate_article_id(article_data.get("url"))

    passed_initial = True
    article_url = article_data.get("url")
    article_title = article_data.get("title", "제목 없음")
    reasons_for_failure = []

    # 1. URL 유효성 검사
    if not article_url or not article_url.startswith(('http://', 'https://')):
        reasons_for_failure.append("INVALID_OR_MISSING_URL")
        passed_initial = False
    else:
        # 2. 하드코딩된 URL 필터링
        for drop_site in HARDCODED_DROP_URLS:
            if drop_site in article_url:
                reasons_for_failure.append(f"HARDCODED_DROP_URL ({drop_site})")
                passed_initial = False
                break

    # 3. 기사 발행 시간 검사 (24시간 이내) - 
    if passed_initial:
        try:
            published_at_str = article_data.get('published_at')
            if not published_at_str:
                reasons_for_failure.append("MISSING_PUBLISHED_AT")
                passed_initial = False
            else:
                # ISO 형식의 날짜 문자열을 datetime 객체로 변환
                published_at = dateutil.parser.isoparse(published_at_str)
                # 타임존 정보가 없으면 UTC로 설정
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
                
                # 현재 UTC 시간과 비교하여 24시간이 지났는지 확인
                if datetime.now(timezone.utc) - published_at > timedelta(hours=24):
                    reasons_for_failure.append("ARTICLE_OLDER_THAN_24H")
                    passed_initial = False
        except (ValueError, TypeError) as e:
            # 날짜 형식이 잘못된 경우
            error_msg = f"INVALID_PUBLISH_AT_FORMAT: {str(e)[:100]}"
            print(f"InitialChecks Task Warning: {error_msg} for URL {article_url}")
            reasons_for_failure.append(error_msg)
            passed_initial = False

    # 4. DB 중복 검사
    if passed_initial:
        if articles_collection is not None and blacklist_collection is not None:
            try:
                query_field = "ID"
                query_value = article_data.get("ID")

                if query_value and articles_collection.count_documents({query_field: query_value}, limit=1) > 0:
                    reasons_for_failure.append("ARTICLES_DB_DUPLICATE_ID")
                    passed_initial = False
                elif query_value and blacklist_collection.count_documents({query_field: query_value}, limit=1) > 0:
                    reasons_for_failure.append("BLACKLIST_DB_DUPLICATE_ID")
                    passed_initial = False
            except Exception as e:
                err_msg = f"MongoDB 중복 확인 중 오류: {e}"
                print(f"InitialChecks Task Warning: {err_msg} {task_id_log}")
                reasons_for_failure.append(f"DB_CHECK_ERROR: {str(e)[:100]}")
                raise self.retry(exc=e, countdown=int(self.request.retries * 60), max_retries=2)
        else:
            print(f"InitialChecks Task Warning: DB 컬렉션이 None이어서 중복 검사를 건너뜜. {task_id_log}")
            reasons_for_failure.append("DB_COLLECTION_IS_NONE_SKIPPING_DUPLICATE_CHECK")

    # 최종 결과 처리
    article_data.setdefault("checked", {})["initial_checks"] = passed_initial
    if not passed_initial:
        reason_str = ", ".join(reasons_for_failure) if reasons_for_failure else "Unknown reason at initial_checks"
        article_data["checked"]["initial_checks_reason"] = reason_str
        print(f"  ➡️ Stage 1 (Initial Checks Task): 실패/드롭됨. 이유: {reason_str}. 기사: {article_url} {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/dropped", "dropped")
        _save_to_blacklist(article_data, blacklist_collection, reason_str)
    else:
        print(f"  ✅ Stage 1 (Initial Checks Task): 통과. 기사: {article_url} {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/passed", "passed")

        content_extraction_task.delay(article_data)
        print(f"  🚀 Stage 1 (Initial Checks Task): Content Extraction Task로 전송. {task_id_log}")

    return {"article_id": article_data.get("ID"), "passed": passed_initial, "reason": article_data.get("checked", {}).get("initial_checks_reason","")}
