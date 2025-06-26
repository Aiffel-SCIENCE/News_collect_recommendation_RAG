# src/pipeline_stages/content_analysis.py
from celery import shared_task
from typing import Tuple
from src.pipeline_stages.embedding_generator import embedding_generation_task # 다음 태스크

# --- 기존 필터링 규칙 및 헬퍼 함수 유지 ---
DROP_WORDS_QUALITY = ["바보", "멍청이", "idiot", "stupid", "광고문의", "스팸입니다"] #
DROP_URLS_QUALITY = ["spammy-domain.com", "adult-site.net"] #

def _check_quality_drop_word(text_content: str): #
    # ... (내용은 원본 파일 참조) ...
    if not text_content: return False #
    for word in DROP_WORDS_QUALITY: #
        if word in text_content.lower(): return True #
    return False #

def _check_quality_drop_url(url: str): #
    # ... (내용은 원본 파일 참조) ...
    if not url: return False #
    for site in DROP_URLS_QUALITY: #
        if site in url: return True #
    return False #

@shared_task(bind=True) # 이 태스크는 외부 I/O가 적어 재시도 필요성 낮을 수 있음
def content_analysis_task(self, article_data: dict):
    task_id_log = f"(Task ID: {self.request.id})" if self.request.id else ""
    print(f"\n📰 Content Analysis Task: 처리 시작 {task_id_log} - {article_data.get('url', 'URL 없음')[:70]}...")
    current_stage_name_path = "stage4_content_analysis_celery"

    # 필요할 때만 가져오기
    import src.celery_app
    save_to_data_folder = src.celery_app.save_to_data_folder

    # 원본 run_content_analysis 함수의 로직을 여기에 적용합니다.
    content = article_data.get("content", "") #
    title = article_data.get("title", "") #
    url = article_data.get("url", "") #
    reasons_for_failure = [] #

    if _check_quality_drop_word(content) or _check_quality_drop_word(title): #
        reasons_for_failure.append("CONTAINS_QUALITY_DROP_WORD") #
    if _check_quality_drop_url(url): #
        reasons_for_failure.append("CONTAINS_QUALITY_DROP_URL") #

    passed_analysis = not bool(reasons_for_failure) #
    if not passed_analysis: #
        article_data.setdefault("checked", {})["content_analysis_reason"] = ", ".join(reasons_for_failure) #


    article_data["checked"]["content_analysis"] = passed_analysis #
    if not passed_analysis: #
        reason = article_data.get("checked", {}).get("content_analysis_reason", "품질 미달") #
        print(f"  ➡️ Stage 4 (Content Analysis Task): 실패/드롭됨. 이유: {reason}. 기사: {url} {task_id_log}") #
        save_to_data_folder(article_data, f"{current_stage_name_path}/dropped", "dropped") #
    else: #
        print(f"  ✅ Stage 4 (Content Analysis Task): 통과. 기사: {url} {task_id_log}") #
        save_to_data_folder(article_data, f"{current_stage_name_path}/passed", "passed") #
        embedding_generation_task.delay(article_data)

    return {"article_id": article_data.get("ID"), "passed": passed_analysis}
