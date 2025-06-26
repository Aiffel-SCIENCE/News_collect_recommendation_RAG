# src/pipeline_stages/finalization.py
import hashlib
import os
from datetime import datetime
from celery import shared_task
import os
import sys
# --- 프로젝트 루트 계산 및 sys.path 수정 ---
_current_file_path = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file_path)))

if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
from src.config_loader.settings import SETTINGS

SIMILARITY_THRESHOLD = SETTINGS.get("SIMILARITY_THRESHOLD_CONTENT", 0.91)
PINECONE_CONTENT_MAX_LENGTH = SETTINGS.get("PINECONE_CONTENT_MAX_LENGTH", 20000)

def generate_article_id(url: str) -> str:
    if not url:
        print("Finalization Task Warning: 빈 URL로 ID 생성 시도. 임의 ID 사용.")
        return f"empty_url_error_{hashlib.sha256(os.urandom(16)).hexdigest()}"
    return hashlib.sha256(url.encode('utf-8')).hexdigest()

def _save_to_mongodb_blacklist(article_doc: dict, blacklist_collection_res, reason_tag: str):
    if blacklist_collection_res is None:
        print(f"Finalization Task Error: 블랙리스트 DB 컬렉션이 제공되지 않아 저장할 수 없습니다: {article_doc.get('url')}")
        return False
    try:
        article_doc.setdefault("checked", {})["dropped_stage"] = "finalization_celery"
        article_doc["checked"]["dropped_reason_tag"] = reason_tag
        article_doc["checked"]["dropped_at"] = datetime.now().isoformat()

        if "ID" not in article_doc or not article_doc["ID"]: # ID가 없는 경우 생성
             article_doc["ID"] = generate_article_id(article_doc.get("url"))

        filter_query = {"ID": article_doc.get("ID")} # ID 필드를 사용하여 쿼리
        update_data = {"$set": article_doc}
        blacklist_collection_res.update_one(filter_query, update_data, upsert=True)
        print(f"  Finalization Task: 기사 '{article_doc.get('title', '')[:30]}...' 블랙리스트({reason_tag}) 저장 완료 (ID: {article_doc.get('ID')}).")
        return True
    except Exception as e:
        print(f"  Finalization Task Error: 블랙리스트 저장 중 오류: {e} for URL {article_doc.get('url')} (ID: {article_doc.get('ID')})")
        return False

def _save_to_mongodb_main(article_doc: dict, articles_collection_res):
    if articles_collection_res is None:
        print(f"Finalization Task Error: 메인 DB 컬렉션이 제공되지 않아 저장할 수 없습니다: {article_doc.get('url')}")
        return False
    try:
        if "ID" not in article_doc or not article_doc["ID"]: # ID가 없는 경우 생성
             article_doc["ID"] = generate_article_id(article_doc.get("url"))

        articles_collection_res.update_one({"ID": article_doc.get("ID")}, {"$set": article_doc}, upsert=True)
        print(f"  Finalization Task: 기사 '{article_doc.get('title', '')[:30]}...' 메인 DB 저장 완료 (ID: {article_doc.get('ID')}).")
        return True
    except Exception as e:
        print(f"  Finalization Task Error: 메인 DB 저장 중 오류: {e} for URL {article_doc.get('url')} (ID: {article_doc.get('ID')})")
        return False

def _upsert_to_pinecone(article_doc: dict, pinecone_manager_res):
    if pinecone_manager_res is None:
        print(f"Finalization Task Error: Pinecone 매니저가 제공되지 않아 업서트할 수 없습니다: {article_doc.get('url')}")
        return False

    article_id = article_doc.get("ID")
    embedding_vector = article_doc.get("embedding")

    if not article_id:
        article_id = generate_article_id(article_doc.get("url"))
        if "empty_url_error" in article_id:
            print(f"Finalization Task Warning: 유효한 ID가 없어 Pinecone 업서트를 건너뜱니다 (URL: {article_doc.get('url')}).")
            return False
        article_doc["ID"] = article_id

    if not embedding_vector:
        print(f"Finalization Task Info: 임베딩 벡터가 없어 Pinecone 업서트를 건너뜁니다 (ID: {article_id}).")
        return False

    pinecone_metadata = {
        "url": article_doc.get("url", ""),
        "title": article_doc.get("title", ""),
        "published_at": article_doc.get("published_at", datetime.now().isoformat()),
        "source": article_doc.get("source", "UnknownSource"),
        "summary": article_doc.get("summary", "")[:1000],
        "content": article_doc.get("content", "")[:PINECONE_CONTENT_MAX_LENGTH], # 실제 content 필드 추가
        #"llm_info_type_categories": article_doc.get("llm_info_type_categories", []),
        #"llm_topic_main_categories": article_doc.get("llm_topic_main_categories", []),
        #"llm_topic_sub_categories": article_doc.get("llm_topic_sub_categories", []),
        "llm_internal_keywords": article_doc.get("llm_internal_keywords", []),
    }
    for key, value in pinecone_metadata.items():
        if value is None:
            pinecone_metadata[key] = ""
        elif isinstance(value, list) and not value:
             pass

    try:
        success = pinecone_manager_res.upsert_vector(vector_id=article_id, vector=embedding_vector, metadata=pinecone_metadata)
        if success:
            print(f"  Finalization Task: 기사 (ID: {article_id}) Pinecone 업서트 성공.")
        else:
            print(f"  Finalization Task Warning: 기사 (ID: {article_id}) Pinecone 업서트 실패 (upsert_vector가 False 반환).")
        return success
    except Exception as e:
        print(f"  Finalization Task Error: Pinecone 업서트 중 오류 (ID: {article_id}): {e}")
        return False


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def finalization_task(self, article_data: dict):
    task_id_log = f"(Task ID: {self.request.id})" if self.request.id else ""
    print(f"\n📰 Finalization Task: 처리 시작 {task_id_log} - {article_data.get('url', 'URL 없음')[:70]}...")
    current_stage_name_path = "stage6_finalization_celery"

    # 필요할 때만 가져오기
    import src.celery_app
    worker_resources = src.celery_app.worker_resources
    save_to_data_folder = src.celery_app.save_to_data_folder

    articles_db_collection = worker_resources.get('articles_collection')
    blacklist_db_collection = worker_resources.get('blacklist_collection')
    pinecone_manager_instance = worker_resources.get('pinecone_manager')

    if articles_db_collection is None or blacklist_db_collection is None or pinecone_manager_instance is None:
        error_msg = (f"DB 또는 Pinecone 매니저 초기화 안됨. "
                     f"Articles Collection is None: {articles_db_collection is None}, "
                     f"Blacklist Collection is None: {blacklist_db_collection is None}, "
                     f"Pinecone Manager is None: {pinecone_manager_instance is None}")
        print(f"❌ Finalization Task CRITICAL: {error_msg} {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/error_resource_init", "error")
        raise Exception(f"Finalization Resources Uninitialized: {error_msg}")

    article_url = article_data.get("url")
    article_embedding = article_data.get("embedding")

    if "ID" not in article_data or not article_data["ID"]:
         article_data["ID"] = generate_article_id(article_url)
    article_id_hash = article_data["ID"]

    is_duplicate_by_similarity = False
    if article_embedding and isinstance(article_embedding, list) and len(article_embedding) > 0:
        try:
            # Pinecone 쿼리 시 메타데이터는 불필요하므로 include_metadata=False로 설정 가능 (성능 약간 향상)
            matches = pinecone_manager_instance.query_vector(vector=article_embedding, top_k=1, include_metadata=True) # Filter3 로직과 일관성을 위해 include_metadata=True 유지
            if matches and matches[0].score >= SIMILARITY_THRESHOLD and matches[0].id != article_id_hash: # 같은 ID를 가진 문서가 아닐 때만 중복으로 판단
                is_duplicate_by_similarity = True
                article_data.setdefault("checked", {})["finalization_reason"] = f"SIMILARITY_DUPLICATE_CONTENT (Score: {matches[0].score:.4f} with ID: {matches[0].id})"
                print(f"  Finalization Task: 기사 (ID: {article_id_hash})는 유사도 중복으로 판단됨 (유사 ID: {matches[0].id}, 점수: {matches[0].score:.4f}).")
            elif matches: # 유사도가 임계값 미만이거나 자기 자신인 경우
                print(f"  Finalization Task: 기사 (ID: {article_id_hash})는 유사도 중복 아님. 유사 ID: {matches[0].id}, 점수: {matches[0].score:.4f}.")
            else: # 매치되는 문서가 없는 경우
                print(f"  Finalization Task: Pinecone에 유사 문서가 없음 (ID: {article_id_hash}).")

        except Exception as e_pinecone_query:
            print(f"  Finalization Task Warning: Pinecone 벡터 쿼리 중 예외: {e_pinecone_query}. 중복 아님으로 처리. {task_id_log}")
            try:
                raise self.retry(exc=e_pinecone_query, countdown=60)
            except Exception:
                 pass # Max retries 초과 등 재시도 실패 시 오류를 무시하고 중복 아님으로 간주하여 진행


    saved_to_main_db = False
    blacklisted = False

    if is_duplicate_by_similarity:
        _save_to_mongodb_blacklist(article_data, blacklist_db_collection, "duplicate_content_similarity_final_celery")
        blacklisted = True
    else:
        mongo_save_success = _save_to_mongodb_main(article_data, articles_db_collection)
        if not mongo_save_success:
            article_data.setdefault("checked", {})["finalization_reason"] = "MONGODB_MAIN_SAVE_FAILED"
            _save_to_mongodb_blacklist(article_data, blacklist_db_collection, "failed_mongodb_main_save_final_celery")
            blacklisted = True
        else:
            saved_to_main_db = True
            if article_embedding and isinstance(article_embedding, list) and len(article_embedding) > 0:
                pinecone_upsert_success = _upsert_to_pinecone(article_data, pinecone_manager_instance)
                if not pinecone_upsert_success:
                    print(f"  Finalization Task Warning: Pinecone 업서트 실패. MongoDB에는 저장됨. URL: {article_url} (ID: {article_id_hash}) {task_id_log}")
                    article_data.setdefault("checked", {})["finalization_note"] = "PINECONE_UPSERT_FAILED_BUT_MONGO_SAVED"
            else:
                 article_data.setdefault("checked", {})["finalization_note"] = "NO_EMBEDDING_FOR_PINECONE"


    article_data.setdefault("checked", {})["finalization_completed"] = True
    article_data["checked"]["saved_to_main_db"] = saved_to_main_db
    article_data["checked"]["blacklisted"] = blacklisted

    if saved_to_main_db and not blacklisted:
        print(f"  🎉 Stage 6 (Finalization Task): 최종 저장 성공! 기사: {article_url} (ID: {article_id_hash}) {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/saved_to_main", "saved")
    elif blacklisted:
        reason = article_data.get("checked", {}).get("finalization_reason", article_data.get("checked",{}).get("dropped_reason_tag", "블랙리스트 처리됨"))
        print(f"  ➡️ Stage 6 (Finalization Task): 블랙리스트 처리됨. 이유: {reason}. 기사: {article_url} (ID: {article_id_hash}) {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/blacklisted", "blacklisted")
    else:
        reason = article_data.get("checked", {}).get("finalization_reason", "알 수 없는 저장 실패")
        print(f"  ➡️ Stage 6 (Finalization Task): 최종 저장 실패 (블랙리스트 아님). 이유: {reason}. 기사: {article_url} (ID: {article_id_hash}) {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/failed_final_save", "failed")


    return {
        "article_id": article_data.get("ID"),
        "saved_to_main_db": saved_to_main_db,
        "blacklisted": blacklisted,
        "generation": article_data.get("generation"),  # 답변 텍스트
        "intent": article_data.get("intent"),          # 답변 타입
        "dashboard_html": article_data.get("dashboard_html"),
        "react_code": article_data.get("react_code"),
        "response_metadata": article_data.get("response_metadata"),
    }
