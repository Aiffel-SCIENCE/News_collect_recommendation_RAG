# src/pipeline_stages/embedding_generator.py

from celery import shared_task
from typing import Tuple, List
from src.pipeline_stages.finalization import finalization_task
import time
from openai import RateLimitError

def _generate_single_embedding(text: str, openai_client, model_name: str) -> list:
    if not openai_client:
        print("EmbeddingGenerator Task Error: OpenAI 클라이언트가 제공되지 않았습니다.")
        return []
    if not text or not text.strip():
        print("EmbeddingGenerator Task Info: 비어있거나 공백만 있는 텍스트이므로 임베딩을 건너뜀.")
        return []
    
    max_retries = 3
    base_delay = 2  # 초기 대기 시간 (초)
    
    for attempt in range(max_retries):
        try:
            response = openai_client.embeddings.create(
                model=model_name,
                input=text
            )
            embedding_vector = response.data[0].embedding
            return embedding_vector
            
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = base_delay * (2 ** attempt)  # 지수 백오프
                print(f"Embedding rate limit reached, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                time.sleep(wait_time)
                continue
            else:
                print(f"Embedding rate limit error after {max_retries} attempts: {e}")
                return []
                
        except Exception as e:
            print(f"EmbeddingGenerator Task Error: 텍스트 임베딩 생성 중 오류: {e}")
            print(f"오류 발생 텍스트 (앞 100자): {text[:100]}...")
            if attempt < max_retries - 1:
                wait_time = base_delay * (2 ** attempt)
                print(f"Embedding error, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                time.sleep(wait_time)
                continue
            else:
                return []
    
    return []


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def embedding_generation_task(self, article_data: dict):
    task_id_log = f"(Task ID: {self.request.id})" if self.request.id else ""
    print(f"\n📰 Embedding Generation Task: 처리 시작 {task_id_log} - {article_data.get('url', 'URL 없음')[:70]}...")
    current_stage_name_path = "stage5_embedding_celery"
    
    # 필요할 때만 가져오기
    import src.celery_app
    worker_resources = src.celery_app.worker_resources
    save_to_data_folder = src.celery_app.save_to_data_folder
    
    openai_client = worker_resources.get('openai_client')
    embedding_model_name = worker_resources.get('embedding_model_name', 'text-embedding-3-small')

    if openai_client is None:
        error_msg = "OpenAI 클라이언트 초기화 안됨."
        print(f"❌ Embedding Generation Task CRITICAL: {error_msg} {task_id_log}")
        article_data["embedding"] = []
        article_data["llm_internal_keywords_embedding"] = []
        article_data.setdefault("checked", {})["embedding_generation_reason"] = "OPENAI_CLIENT_NOT_INITIALIZED_CELERY"
        save_to_data_folder(article_data, f"{current_stage_name_path}/failed_or_skipped", "skipped_model_error")
        raise Exception(f"OpenAI Client Uninitialized: {error_msg}")

    # 1. 콘텐츠 임베딩 생성
    title_for_embedding = article_data.get("title", "")
    content_for_embedding = article_data.get("content", "")
    text_to_embed = f"{title_for_embedding}\n{content_for_embedding}".strip()

    embedded = False
    if not text_to_embed:
        article_data["embedding"] = []
        article_data.setdefault("checked", {})["embedding_generation_reason"] = "NO_TEXT_TO_EMBED_CELERY"
    else:
        try:
            embedding_vector = _generate_single_embedding(text_to_embed, openai_client, embedding_model_name)
            article_data["embedding"] = embedding_vector
            if embedding_vector:
                embedded = True
            else:
                article_data.setdefault("checked", {})["embedding_generation_reason"] = "EMBEDDING_FAILED_EMPTY_VECTOR_CELERY"
        except Exception as e_embed:
            print(f"Embedding Generation Task Error during _generate_single_embedding (content): {e_embed} {task_id_log}")
            article_data["embedding"] = []
            article_data.setdefault("checked", {})["embedding_generation_reason"] = f"CONTENT_EMBEDDING_EXCEPTION: {str(e_embed)[:100]}"
            raise self.retry(exc=e_embed)

    # 2. LLM 키워드 임베딩 생성 
    keywords = article_data.get("llm_internal_keywords", [])
    individual_keyword_embeddings = [] # 개별 임베딩을 저장할 리스트

    if keywords and openai_client:
        print(f"  ✨ Stage 5 (Embedding Generation Task): LLM 키워드 {len(keywords)}개 개별 임베딩 시작...")
        for keyword in keywords:
            try:
                # 각 키워드를 개별적으로 임베딩
                kw_embedding_vector = _generate_single_embedding(keyword, openai_client, embedding_model_name)
                if kw_embedding_vector:
                    individual_keyword_embeddings.append(kw_embedding_vector)
            except Exception as e_kw_embed:
                print(f"  ⚠️ Stage 5 (Embedding Generation Task): 키워드 '{keyword}' 임베딩 중 오류: {e_kw_embed}")
        
        # 새로 생성된 개별 키워드 임베딩 리스트를 저장
        article_data["llm_individual_keyword_embeddings"] = individual_keyword_embeddings
        # 기존 필드는 제거하거나 비워둠
        article_data["llm_internal_keywords_embedding"] = [] 
        
        if individual_keyword_embeddings:
            print(f"  ✅ Stage 5 (Embedding Generation Task): LLM 키워드 개별 임베딩 생성 완료. (성공: {len(individual_keyword_embeddings)}개)")
    else:
        # 키워드가 없는 경우, 필드를 빈 리스트로 초기화
        article_data["llm_individual_keyword_embeddings"] = []
        article_data["llm_internal_keywords_embedding"] = []

    article_data.setdefault("checked", {})["embedding_generation"] = embedded
    if not embedded:
        print(f"  ⚠️ Stage 5 (Embedding Generation Task): 콘텐츠 임베딩 생성 실패 또는 건너뜀. 기사: {article_data.get('url')} {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/failed_or_skipped", "skipped")
    else:
        print(f"  ✅ Stage 5 (Embedding Generation Task): 콘텐츠 임베딩 성공. 기사: {article_data.get('url')} {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/passed", "passed")

    finalization_task.delay(article_data)
    return {"article_id": article_data.get("ID"), "embedded": embedded}
