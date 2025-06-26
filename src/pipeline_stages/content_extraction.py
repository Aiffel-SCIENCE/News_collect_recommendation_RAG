# src/pipeline_stages/content_extraction.py
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from newspaper import Article as NewspaperArticle, Config as NewspaperConfig, ArticleException
import nltk
import ssl
import requests
from requests.exceptions import SSLError as RequestsSSLError
from typing import Tuple, Optional, Dict
import sys
from celery import shared_task
import src.celery_app


_current_file_path = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file_path)))
print(f"DEBUG (content_extraction.py): 현재 파일 경로: {_current_file_path}")
print(f"DEBUG (content_extraction.py): 계산된 프로젝트 루트: {_project_root}")

if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
    print(f"DEBUG (content_extraction.py): sys.path에 추가됨: {_project_root}")
else:
    print(f"DEBUG (content_extraction.py): {_project_root}는 이미 sys.path에 있습니다.")
from src.pipeline_stages.categorization import categorization_task
from src.pipeline_stages.content_analysis import content_analysis_task
from src.config_loader.settings import SETTINGS
REPLACEMENT_CHAR = SETTINGS.get("REPLACEMENT_CHAR", '\ufffd')

_nltk_punkt_initialized = False
def initialize_nltk_punkt_once():
    global _nltk_punkt_initialized
    if _nltk_punkt_initialized:
        return
    try:
        nltk.data.find('tokenizers/punkt')
        # print("ContentExtraction Task: 'punkt' 토크나이저 이미 다운로드됨.")
    except LookupError:
        print("ContentExtraction Task: 'punkt' 토크나이저 다운로드 시도...")
        try:
            try: _create_unverified_https_context = ssl._create_unverified_context
            except AttributeError: pass
            else: ssl._create_default_https_context = _create_unverified_https_context
            nltk.download('punkt', quiet=True, raise_on_error=True)
            nltk.data.find('tokenizers/punkt')
            print("ContentExtraction Task: 'punkt' 다운로드 및 확인 완료.")
        except Exception as e_nltk:
            print(f"ContentExtraction Task Error: 'punkt' 자동 다운로드 중 오류: {e_nltk}")
            raise RuntimeError(f"NLTK Punkt 다운로드 실패: {e_nltk}")
    except Exception as e_nltk_find:
         print(f"ContentExtraction Task Error: NLTK 'punkt' 확인 중 오류: {e_nltk_find}")
         raise RuntimeError(f"NLTK Punkt 확인 실패: {e_nltk_find}")
    _nltk_punkt_initialized = True


# --- Aigen_science/src/processor/processor.py의 fetch_article_with_newspaper3k 로직 통합 ---
def fetch_article_with_newspaper3k(url: str, language_code='ko') -> Optional[Dict]:
    if not url:
        return None
    config = NewspaperConfig()
    config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'
    config.request_timeout = 15
    config.memoize_articles = False
    config.fetch_images = False
    article_parser = NewspaperArticle(url, language=language_code, config=config)
    try:
        article_parser.download()
        if article_parser.download_state != 2: # SUCCESS
            return None
        article_parser.parse()
        title = article_parser.title
        text = article_parser.text
        publish_date_obj = article_parser.publish_date

        publish_date_str = None
        if isinstance(publish_date_obj, datetime):
            publish_date_str = publish_date_obj.isoformat()

        return {"title_extracted": title, "content_extracted": text, "publish_date_extracted": publish_date_str}
    except ArticleException as e:
        return None
    except Exception as e:
        return None

# --- Aigen_science/src/processor/processor.py의 fetch_content_with_beautifulsoup 로직 통합 ---
def fetch_content_with_beautifulsoup(url: str, is_naver_news: bool = False) -> Optional[str]:
    if not url: return None
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'})
    response = None
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
    except RequestsSSLError:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = session.get(url, timeout=10, verify=False)
            response.raise_for_status()
        except Exception:
            return None
    except Exception:
        return None

    if response is None: return None

    html_content_bytes = response.content
    decoded_html_text = None
    potential_encodings = ['utf-8']
    if response.encoding:
        potential_encodings.append(response.encoding.lower())
    if response.apparent_encoding:
        potential_encodings.append(response.apparent_encoding.lower())
    potential_encodings.extend(['euc-kr', 'cp949', 'iso-8859-1'])

    unique_encodings = []
    for enc in potential_encodings:
        if enc and enc not in unique_encodings:
            unique_encodings.append(enc)

    for enc in unique_encodings:
        try:
            decoded_html_text = html_content_bytes.decode(enc)
            if REPLACEMENT_CHAR not in decoded_html_text:
                break
            decoded_html_text = None
        except UnicodeDecodeError:
            decoded_html_text = None
        except Exception:
            decoded_html_text = None

    if decoded_html_text is None:
        decoded_html_text = html_content_bytes.decode('utf-8', errors='replace')


    try:
        soup = BeautifulSoup(decoded_html_text, 'html.parser')
        article_body = None
        if is_naver_news:
            naver_selectors = [
                {'tag': 'div', 'attrs': {'id': 'dic_area'}},
                {'tag': 'div', 'attrs': {'class': 'newsct_article _article_body'}},
                {'tag': 'article', 'attrs': {'id': 'dic_area'}},
                {'tag': 'section', 'attrs': {'class': 'article-body'}},]
            for selector in naver_selectors:
                article_body = soup.find(selector['tag'], **selector['attrs'])
                if article_body: break
        if not article_body:
            general_selectors = [
                {'tag': 'article', 'attrs': {}},
                {'tag': 'div', 'attrs': {'class': re.compile(r'article-content|article_body|post-content|entry-content|본문|article_view|articleBody|content|view_content', re.I)}},
                {'tag': 'main', 'attrs': {}},
                {'tag': 'div', 'attrs': {'id': re.compile(r'article_body|content|articleContent|realContent|viewContent', re.I)}},]
            for selector in general_selectors:
                article_body = soup.find(selector['tag'], **selector['attrs'])
                if article_body: break

        text_content = ""
        if article_body:
            for tag_to_remove in article_body.find_all(['script', 'style', 'aside', 'nav', 'footer', 'form', 'iframe', 'noscript', 'figure', 'figcaption', 'header',
                                                       'div.link_news', 'div.reporter_area', 'div.NCOMMENT', 'div#comment',
                                                       lambda tag: tag.has_attr('class') and any(cls in tag['class'] for cls in ['ad', 'banner', 'popup', 'related', 'share', 'comment', 'social', 'advertisement', 'widget', 'kst_link', 'link_news', 'journalistcard_card_article']) or
                                                                   tag.has_attr('id') and any(id_val in tag['id'] for id_val in ['ad', 'banner', 'popup', 'related', 'share', 'comment', 'social', 'advertisement', 'widget', 'ifr_recomm']) ]):
                if hasattr(tag_to_remove, 'decompose'): tag_to_remove.decompose()

            if is_naver_news:
                div_texts = [div.get_text(separator='\n', strip=True) for div in article_body.find_all(['div', 'p', 'span'], recursive=False) if div.get_text(strip=True) and len(div.get_text(strip=True)) > 10]
                if div_texts: text_content = "\n".join(div_texts)
                else: text_content = article_body.get_text(separator='\n', strip=True)
            else:
                paragraphs = article_body.find_all('p')
                if paragraphs:
                    extracted_paragraphs = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True) and len(p.get_text(strip=True)) > 20]
                    if extracted_paragraphs: text_content = "\n".join(extracted_paragraphs)
                    else: text_content = article_body.get_text(separator=' ', strip=True)
                else: text_content = article_body.get_text(separator=' ', strip=True)
        else:
            for tag_to_remove_global in soup.find_all(['script', 'style', 'aside', 'nav', 'footer', 'header', 'form', 'iframe', 'noscript',
                                                    lambda tag: tag.has_attr('class') and any(cls in tag['class'] for cls in ['ad', 'banner', 'popup', 'related', 'share', 'comment', 'social', 'advertisement', 'widget']) or
                                                                tag.has_attr('id') and any(id_val in tag['id'] for id_val in ['ad', 'banner', 'popup', 'related', 'share', 'comment', 'social', 'advertisement', 'widget'])]):
                if hasattr(tag_to_remove_global, 'decompose'): tag_to_remove_global.decompose()
            text_content = soup.get_text(separator=' ', strip=True)

        if text_content and REPLACEMENT_CHAR in text_content:
            pass
        return text_content
    except Exception as e_parsing:
        return None

# --- Aigen_science/src/processor/processor.py의 get_html_for_llm 로직 통합 ---
def get_html_for_llm(url: str) -> Optional[str]:
    if not url: return None
    try:
        headers = {'User-Agent': 'Googlebot/2.1 (+http://www.google.com/bot.html)'}
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()

        html_content_bytes = response.content
        decoded_html = None
        try:
            decoded_html = html_content_bytes.decode('utf-8')
            if REPLACEMENT_CHAR in decoded_html: decoded_html = None
        except UnicodeDecodeError:
            pass

        if not decoded_html and response.apparent_encoding:
            try:
                decoded_html = html_content_bytes.decode(response.apparent_encoding, errors='replace')
            except UnicodeDecodeError:
                pass

        if not decoded_html:
             decoded_html = html_content_bytes.decode('utf-8', errors='replace')

        return decoded_html
    except requests.exceptions.RequestException as e:
        return None
    except Exception as e_general:
        return None

# --- Aigen_science/src/processor/processor.py의 try_llm_content_extraction_from_html 로직 통합 ---
def try_llm_content_extraction_from_html(url: str, html_content: str, openai_client) -> Optional[str]:
    if not openai_client:
        print("ContentExtraction (LLM Extract): OpenAI 클라이언트가 제공되지 않아 LLM 추출을 건너뜁니다.")
        return None
    if not html_content:
        return None

    LLM_EXTRACTION_MODEL = SETTINGS.get("OPENAI_LLM_EXTRACTION_MODEL", "gpt-4.1-nano")
    html_snippet_for_llm = html_content[:80000]
    prompt = f"""
    당신은 HTML 문서에서 특정 내용을 **그대로, 단 한 글자도 빠짐없이, 어떠한 요약이나 수정, 재구성도 하지 않고** 추출하는 매우 정밀한 로봇입니다.
    당신의 임무는 주어진 HTML에서 오직 뉴스 기사의 본문 전체를 시작부터 끝까지 문자 그대로 복사하는 것입니다.
    **절대 준수 규칙:**
    1.  **요약 금지**: 절대로 내용을 요약하거나 짧게 만들지 마세요.
    2.  **내용 변경 금지**: 단어 하나, 문장 하나도 임의로 변경하거나 다른 표현으로 바꾸지 마세요. 원문 그대로 추출해야 합니다.
    3.  **생략 금지**: 기사 본문에 해당하는 모든 문장과 문단을 시작부터 끝까지 전부 포함해야 합니다. 중간에 내용을 자르거나 생략하면 안 됩니다.
    4.  **부가 요소 완벽 제거**: 광고, 메뉴, 사이드바, 관련 기사 링크 목록, 댓글, SNS 공유 버튼, 저작권 고지 등 기사 본문이 아닌 모든 것은 철저히 제거해주세요.
    5.  **형식 유지**: 원본 기사의 문단 구분(줄바꿈)을 최대한 따라서 출력해주세요.
    6.  **출처 정보 포함 (선택 사항, 필요한 경우)**: 만약 기사 본문 바로 뒤에 '출처: [언론사명]' 또는 유사한 형태의 출처 정보가 명확히 있다면, 해당 줄까지 포함하여 추출해주세요. (만약 이 지시가 방해가 된다면 무시해도 좋습니다.)
    아래 제공된 HTML 내용에서 위 규칙들을 철저히 지켜 뉴스 기사 본문 전체를 추출해주세요.
    HTML 내용:
    ```html
    {html_snippet_for_llm}
    ```
    정제된 기사 본문:
    """
    try:
        completion = openai_client.chat.completions.create(
            model=LLM_EXTRACTION_MODEL,
            messages=[
                {"role": "system", "content": "당신은 HTML에서 뉴스 기사 본문을 원문 그대로, 어떠한 변경이나 요약 없이 추출하는 초정밀 AI 도구입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=3500
        )
        content = completion.choices[0].message.content.strip()
        if "본문 추출 불가" in content or len(content) < 50:
            return None
        return content
    except Exception as e:
        return None

# --- Aigen_science/src/processor/processor.py의 final_text_clean 로직 통합 ---
def final_text_clean(text: str) -> str:
    if not isinstance(text, str) or not text.strip(): return ""
    text = text.replace(REPLACEMENT_CHAR, " ")
    soup = BeautifulSoup(text, "html.parser")
    text_no_html = soup.get_text(separator=' ', strip=True)
    cleaned_text = re.sub(r"[^a-zA-Z0-9ㄱ-ㅎ가-힣.?!,%\s]", " ", text_no_html)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    cleaned_text = cleaned_text.lower()
    return cleaned_text

LLM_SUMMARY_MODEL = SETTINGS.get("OPENAI_LLM_SUMMARY_MODEL", "gpt-4.1-nano") # config.yaml에 추가 필요

# --- 새로운 LLM 요약 함수 추가 ---
def _summarize_with_llm(text_content: str, openai_client) -> str:
    if not openai_client or not text_content or len(text_content.strip()) < 100: # 최소 100자 이상 텍스트에 대해 요약 시도
        return "" # 요약할 텍스트가 없거나 너무 짧으면 빈 문자열 반환

    content_for_llm = text_content[:8000] # 요약할 텍스트 길이 제한 (본문보다 짧게)

    system_prompt = "당신은 주어진 뉴스 기사 본문을 5줄 이하로 간결하게 요약하는 전문 AI입니다. 핵심 내용만 포함하고, 불필요한 서론이나 결론 없이 바로 본문 요약을 제공해주세요. 요약은 한국어로 제공 되어야 합니다."
    user_prompt = (
        f"다음 뉴스 기사 본문을 6줄 이하로 요약해주세요:\n\n"
        f"본문:\n{content_for_llm}\n\n"
        f"요약:"
    )

    try:
        completion = openai_client.chat.completions.create(
            model=LLM_SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5, # 요약의 창의성 조절
            max_tokens=300 # 6줄 요약에 적절한 토큰 수 (대략 1줄 50토큰 * 6줄)
        )
        summary = completion.choices[0].message.content.strip()
        print(f"  ContentExtraction (LLM Summary): LLM으로 요약 생성 완료 (길이: {len(summary)}).")
        return summary
    except Exception as e:
        print(f"  ContentExtraction (LLM Summary): LLM 요약 생성 중 오류 발생: {e}")
        return "" # 오류 발생 시 빈 문자열 반환
    
# --- content_extraction_task 내에서 LLM 요약 함수 호출 ---
@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def content_extraction_task(self, article_data: dict):
    task_id_log = f"(Task ID: {self.request.id})" if self.request.id else ""
    print(f"\n📰 Content Extraction Task: 처리 시작 {task_id_log} - {article_data.get('url', 'URL 없음')[:70]}...")
    current_stage_name_path = "stage2_content_extraction_celery"

    # 필요할 때만 가져오기
    worker_resources = src.celery_app.worker_resources
    save_to_data_folder = src.celery_app.save_to_data_folder

    try:
        initialize_nltk_punkt_once()
    except RuntimeError as e:
        print(f"❌ Content Extraction Task CRITICAL: NLTK 초기화 실패: {e} {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/error_nltk_init", "error")
        raise self.retry(exc=e, countdown=300, max_retries=1)

    openai_client_for_extraction = worker_resources.get('openai_client')

    article_url = article_data.get("url")
    original_title = article_data.get("title", "제목 없음 (원본)")
    article_summary_original = article_data.get("summary", "")
    article_source_tag = article_data.get("source", "").upper()

    content_candidate = None
    content_source_log = "pending_extraction"
    extracted_title_candidate = None
    extracted_publish_date_candidate_str = None

    is_naver_news_link = bool(article_url and ("n.news.naver.com/mnews/article" in article_url or "sports.naver.com" in article_url)) # 수정된 코드

    # 콘텐츠 추출 전략 (원본 함수의 로직을 최대한 따름)
    if is_naver_news_link:
        content_candidate = fetch_content_with_beautifulsoup(article_url, is_naver_news=True)
        content_source_log = "beautifulsoup_naver"
        if not (content_candidate and len(content_candidate.strip()) > 50):
            extracted_np_data = fetch_article_with_newspaper3k(article_url)
            if extracted_np_data and extracted_np_data.get("content_extracted") and \
               len(extracted_np_data["content_extracted"].strip()) > 50:
                content_candidate = extracted_np_data["content_extracted"]
                content_source_log = "newspaper3k_after_bs_fail_naver"
                if extracted_np_data.get("title_extracted"): extracted_title_candidate = extracted_np_data["title_extracted"]
                if extracted_np_data.get("publish_date_extracted"): extracted_publish_date_candidate_str = extracted_np_data["publish_date_extracted"]
            else:
                content_candidate = None
    else: # 일반 URL
        extracted_np_data = fetch_article_with_newspaper3k(article_url)
        if extracted_np_data and extracted_np_data.get("content_extracted") and \
           len(extracted_np_data["content_extracted"].strip()) > 50:
            content_candidate = extracted_np_data["content_extracted"]
            content_source_log = "newspaper3k_general"
            if extracted_np_data.get("title_extracted"): extracted_title_candidate = extracted_np_data["title_extracted"]
            if extracted_np_data.get("publish_date_extracted"): extracted_publish_date_candidate_str = extracted_np_data["publish_date_extracted"]
        else:
            content_candidate = fetch_content_with_beautifulsoup(article_url, is_naver_news=False)
            content_source_log = "beautifulsoup_general_fallback"
            if not (content_candidate and len(content_candidate.strip()) > 50):
                content_candidate = None

    if not (content_candidate and len(content_candidate.strip()) > 50) and article_source_tag != "DART":
        html_for_llm = get_html_for_llm(article_url)
        if html_for_llm and openai_client_for_extraction:
            llm_extracted_content = try_llm_content_extraction_from_html(article_url, html_for_llm, openai_client_for_extraction)
            if llm_extracted_content and len(llm_extracted_content.strip()) > 50:
                content_candidate = llm_extracted_content
                content_source_log = "llm_extraction_from_html"
        elif not openai_client_for_extraction:
             content_source_log += "_llm_skipped_no_client"
        else:
            content_source_log += "_llm_skipped_no_html"

    final_content_text = content_candidate if content_candidate is not None else ""

    # 제목 업데이트
    if extracted_title_candidate:
        article_data["title"] = final_text_clean(extracted_title_candidate)
    else:
        article_data["title"] = final_text_clean(original_title)

    # 발행일 업데이트 (Newspaper3k가 더 정확한 값을 제공했을 경우)
    if extracted_publish_date_candidate_str:
        article_data["published_at"] = extracted_publish_date_candidate_str

    # final_content_text가 확정된 후 요약 생성
    article_data["content"] = final_text_clean(final_content_text)

    # **여기서 LLM 요약을 수행합니다.**
    # 추출된 본문이 있고 OpenAI 클라이언트가 있다면 요약 생성
    if article_data["content"] and openai_client_for_extraction:
        llm_generated_summary = _summarize_with_llm(article_data["content"], openai_client_for_extraction)
        if llm_generated_summary:
            article_data["summary"] = llm_generated_summary # LLM 요약으로 summary 필드 업데이트
            print(f"  ✅ Stage 2 (Content Extraction Task): LLM 요약 완료.")
        else:
            # LLM 요약 실패 시 기존 요약 (collector에서 온 것)을 정제하여 사용
            article_data["summary"] = final_text_clean(article_summary_original)
            print(f"  ⚠️ Stage 2 (Content Extraction Task): LLM 요약 실패. 기존 요약 정제본 사용.")
    else:
        # 본문이 없거나 LLM 클라이언트가 없다면 기존 요약 정제본 사용
        article_data["summary"] = final_text_clean(article_summary_original)
        print(f"  ℹ️ Stage 2 (Content Extraction Task): LLM 요약 건너뜀 (본문 없음/클라이언트 없음). 기존 요약 정제본 사용.")


    article_data.setdefault("checked", {})
    article_data["checked"]["content_source_log"] = content_source_log

    extracted_successfully = False
    # 성공 여부 판단 (원본 로직 유지)
    if article_source_tag == "DART":
        if article_data.get("title") or article_data.get("summary"):
             extracted_successfully = True
        else:
            article_data["checked"]["content_extraction_reason"] = "DART_CONTENT_MISSING"
    elif len(article_data["content"].strip()) > 50:
        extracted_successfully = True
    else:
        article_data["checked"]["content_extraction_reason"] = "INSUFFICIENT_CONTENT_LENGTH"


    article_data["checked"]["content_extraction"] = extracted_successfully
    if not extracted_successfully:
        reason = article_data.get("checked", {}).get("content_extraction_reason", "콘텐츠 부족")
        print(f"  ➡️ Stage 2 (Content Extraction Task): 실패. 이유: {reason}. 기사: {article_url} {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/failed", "failed")
        # 콘텐츠 추출 실패 시 파이프라인 중단 (다음 태스크 호출 안 함)
    else:
        print(f"  ✅ Stage 2 (Content Extraction Task): 성공. 기사: {article_url} {task_id_log}")
        save_to_data_folder(article_data, f"{current_stage_name_path}/passed", "passed")
        # 다음 태스크 결정 (Categorization 활성화 여부에 따라)
        if SETTINGS.get("LLM_CATEGORIZATION", {}).get("ENABLED", False):
            categorization_task.delay(article_data)
        else:
            print(f"  ℹ️ Stage 3 (Categorization Task): 비활성화됨. Content Analysis Task로 진행. {task_id_log}")
            article_data["checked"]["categorization"] = "skipped_disabled"
            content_analysis_task.delay(article_data)

    return {"article_id": article_data.get("ID"), "extracted": extracted_successfully}
