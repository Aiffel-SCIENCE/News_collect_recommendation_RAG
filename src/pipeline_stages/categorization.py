# src/pipeline_stages/categorization.py
import traceback
from celery import shared_task
from typing import List
import os
import sys
import time
from openai import RateLimitError

# --- 프로젝트 루트 계산 및 sys.path 수정 ---
_current_file_path = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file_path)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.config_loader.settings import SETTINGS
from src.pipeline_stages.content_analysis import content_analysis_task


def _call_llm_for_list_output(prompt_text: str, openai_client, model_name: str, expected_items: int) -> list:
    """LLM을 호출하여 쉼표로 구분된 리스트를 반환받는 헬퍼 함수"""
    if not openai_client: return []
    
    max_retries = 3
    base_delay = 2  # 초기 대기 시간 (초)
    
    for attempt in range(max_retries):
        try:
            completion = openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are an AI assistant that provides responses as comma-separated lists."},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.2,
                max_tokens=200 # 키워드 추출에 충분한 토큰
            )
            raw_output = completion.choices[0].message.content or ""
            parsed_list = [item.strip() for item in raw_output.strip().split(',') if item.strip()]
            return parsed_list[:expected_items]
            
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = base_delay * (2 ** attempt)  # 지수 백오프
                print(f"Rate limit reached, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                time.sleep(wait_time)
                continue
            else:
                print(f"Rate limit error after {max_retries} attempts: {e}")
                return []
                
        except Exception as e:
            print(f"Categorization LLM call error: {e}")
            if attempt < max_retries - 1:
                wait_time = base_delay * (2 ** attempt)
                print(f"LLM error, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                time.sleep(wait_time)
                continue
            else:
                return []
    
    return []

def extract_llm_internal_keywords(text_content: str, openai_client) -> list:
    """LLM을 사용하여 텍스트에서 핵심 키워드를 추출하는 함수"""
    if not openai_client or not text_content or len(text_content.strip()) < 20: return []
    
    # config.yaml에서 최대 키워드 개수 설정 가져오기 (없으면 기본값 10 사용)
    num_keywords = SETTINGS.get("LLM_CATEGORIZATION", {}).get("MAX_INTERNAL_KEYWORDS", 10)
    keyword_model = SETTINGS.get("OPENAI_KEYWORD_MODEL", "gpt-4.1-nano")
    content_for_llm = text_content[:4000]

    system_prompt = "당신은 주어진 텍스트의 핵심 주제를 완벽하게 관통하는 주요 키워드를 추출하는 AI입니다."
    user_prompt = (
        f"다음 텍스트의 내용을 가장 잘 대표하는 핵심 키워드를 3개에서 {num_keywords}개 사이로 추출해주세요. "
        f"반드시 기사 전체의 핵심 의미를 관통하는 단어들이어야 합니다. "
        f"각 키워드는 명사 또는 명사구 형태여야 하며, 쉼표로 구분된 리스트 형식으로만 답변해주세요.\n\n"
        f"텍스트:\n{content_for_llm}\n\n"
        f"주요 키워드 (3~{num_keywords}개, 쉼표로 구분):"
    )
    return _call_llm_for_list_output(user_prompt, openai_client, keyword_model, num_keywords)


@shared_task(bind=True, max_retries=2, default_retry_delay=180)
def categorization_task(self, article_data: dict):
    """
    Celery Task: 기사 내용에서 핵심 키워드만 추출합니다.
    (카테고리 분류 기능은 제거됨)
    """
    task_id_log = f"(Task ID: {self.request.id})" if self.request.id else ""
    print(f"\n📰 Categorization Task (Keywords Only): 처리 시작 {task_id_log} - {article_data.get('url', 'URL 없음')[:70]}...")
    current_stage_name_path = "stage3_categorization_celery"

    # 필요할 때만 가져오기
    import src.celery_app
    worker_resources = src.celery_app.worker_resources
    save_to_data_folder = src.celery_app.save_to_data_folder

    # DART 공시는 키워드 추출 없이 통과
    if article_data.get("source") == "DART":
        print(f"  ℹ️ Stage 3 (Categorization Task): DART 출처이므로 키워드 추출을 건너뜁니다. {task_id_log}")
        article_data["llm_internal_keywords"] = []
        article_data.setdefault("checked", {})["categorization"] = True
        article_data["checked"]["categorization_reason"] = "SKIPPED_IS_DART"
        save_to_data_folder(article_data, f"{current_stage_name_path}/passed_dart", "passed")
        content_analysis_task.delay(article_data)
        return {"article_id": article_data.get("ID"), "categorized": True, "reason": "DART_SKIPPED"}

    openai_client_for_nlp = worker_resources.get('openai_client')
    if not openai_client_for_nlp:
        print(f"❌ Categorization Task WARNING: OpenAI 클라이언트가 없어 건너뜁니다. {task_id_log}")
        article_data["llm_internal_keywords"] = []
        article_data.setdefault("checked", {})["categorization_reason"] = "NO_OPENAI_CLIENT"
        article_data["checked"]["categorization"] = False
        save_to_data_folder(article_data, f"{current_stage_name_path}/skipped_no_client", "skipped")
        content_analysis_task.delay(article_data)
        return {"article_id": article_data.get("ID"), "categorized": False}

    content_to_analyze = (article_data.get("content", "") or (article_data.get("title", "") + " " + article_data.get("summary", ""))).strip()
    categorized_successfully = False

    if not content_to_analyze:
        article_data["llm_internal_keywords"] = []
        article_data.setdefault("checked", {})["categorization_reason"] = "NO_TEXT_FOR_ANALYSIS"
    else:
        try:
            # --- 키워드 추출만 수행 ---
            keywords = extract_llm_internal_keywords(content_to_analyze, openai_client_for_nlp)
            article_data["llm_internal_keywords"] = keywords
            categorized_successfully = bool(keywords)
        except Exception as e:
            print(f"Categorization Task LLM Error: {e} {task_id_log}")
            article_data.setdefault("checked", {})["categorization_reason"] = f"LLM_ERROR: {str(e)[:100]}"
            raise self.retry(exc=e)

    article_data.setdefault("checked", {})["categorization"] = categorized_successfully
    if categorized_successfully:
        print(f"  ✅ Stage 3 (Categorization Task): 키워드 추출 성공. 기사: {article_data.get('url')} {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/passed", "passed")
    else:
        reason = article_data.get("checked", {}).get("categorization_reason", "키워드 추출 실패")
        print(f"  ⚠️ Stage 3 (Categorization Task): 실패 또는 건너뜀. 이유: {reason}. 기사: {article_data.get('url')} {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/skipped_or_failed", "skipped")

    # 다음 단계인 content_analysis_task로 전달
    content_analysis_task.delay(article_data)
    
    return {"article_id": article_data.get("ID"), "categorized": categorized_successfully}
