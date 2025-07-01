# src/news_collector/news_collector.py
import os
import sys
import requests
import html
import json
import feedparser
from datetime import datetime, timedelta
import re
from dateutil.parser import parse as date_parse

# --- 프로젝트 루트 계산 및 sys.path 수정 ---
_current_file_path = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(_current_file_path)))
print(f"DEBUG (news_collector.py): 현재 파일 경로: {_current_file_path}")
print(f"DEBUG (news_collector.py): 계산된 프로젝트 루트: {_project_root}")

if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
    print(f"DEBUG (news_collector.py): sys.path에 추가됨: {_project_root}")
else:
    print(f"DEBUG (news_collector.py): {_project_root}는 이미 sys.path에 있습니다.")

from src.pipeline_stages.initial_checks import initial_checks_task
from src.config_loader.settings import SETTINGS

# 설정값 가져오기
DART_API_KEY = SETTINGS.get("DART_API_KEY")
NAVER_CLIENT_ID = SETTINGS.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = SETTINGS.get("NAVER_CLIENT_SECRET")
RAW_DATA_PATH = SETTINGS.get("RAW_DATA_PATH")

redis_client = None

def process_and_store_article(article_data):
    processed_article = {
        "title": article_data.get("title", ""),
        "content": "",
        "url": article_data.get("url", ""),
        "published_at": format_published_date(article_data.get("published_at")),
        "summary": article_data.get("summary", ""),
        "embedding": [],
        "source": article_data.get("source", "Unknown"),
        #"llm_info_type_categories": [],
        #"llm_topic_main_categories": [],
        #"llm_topic_sub_categories": [],
        "llm_internal_keywords": [],
        "checked": {}
    }
    save_to_raw_data_folder(processed_article)
    try:
        initial_checks_task.delay(processed_article)
        print(f"🚀 Collector: '{processed_article.get('title')[:30]}...' initial_checks_task로 전송됨.")
    except Exception as e:
        print(f"⚠️ 경고: Celery 태스크 호출 실패 (initial_checks_task): {e}")
    return processed_article

def save_to_raw_data_folder(article):
    # Raw 데이터 JSON 파일 저장을 비활성화
    # raw_data_dir = os.path.join(_project_root, RAW_DATA_PATH)
    # os.makedirs(raw_data_dir, exist_ok=True)
    # filename_safe_title = re.sub(r'[\\/*?:"<>| ]', '_', article.get("title", "no_title"))[:50].strip()
    # timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    # filename = f"{filename_safe_title}_{timestamp}.json"
    # filepath = os.path.join(raw_data_dir, filename)
    # with open(filepath, 'w', encoding='utf-8') as f:
    #     json.dump(article, f, ensure_ascii=False, indent=4)
    # print(f"📁 raw 데이터 저장됨: {filepath}")
    
    # Raw 데이터 JSON 파일 저장이 비활성화되었습니다
    pass

def format_published_date(date_str):
    if not date_str or date_str == 'No Publish Date Available':
        return None
    try:
        dt_obj = date_parse(date_str)
        return dt_obj.isoformat()
    except Exception as e:
        print(f"⚠️ 날짜 파싱 오류: '{date_str}' - {e}")
        return None


def collect_from_api_file(filepath="api_sources.txt"): #
    articles = []
    sources_dir = os.path.join(_project_root, "src", "sources")
    sources_filepath = os.path.join(sources_dir, filepath)

    naver_headers = None
    if NAVER_CLIENT_ID and NAVER_CLIENT_SECRET:
        naver_headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }
        print("✅ 네이버 API 키 로드 성공 (settings.py를 통해 config.yaml에서)")
    else:
        print("⚠️ 네이버 API 키가 없어 네이버 API 수집 시도 시 실패할 수 있습니다. config.yaml 파일을 확인하세요.")

    urls = []
    print(f"✅ '{filepath}'에서 API 소스 URL 로드 시도...")
    try:
        with open(sources_filepath, "r", encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        print(f"✅ '{filepath}'에서 {len(urls)}개의 API 소스 URL 로드 완료")
    except FileNotFoundError:
        print(f"❌ 에러: API 소스 파일({sources_filepath})을 찾을 수 없습니다.")
        return articles
    except Exception as e:
        print(f"❌ 에러: API 소스 파일({sources_filepath})을 읽는 중 오류 발생: {e}")
        return articles


    print("\n🌐 API 수집 시작...")
    for url in urls:
        if not url.startswith('http'):
            print(f"⚠️ 유효하지 않은 URL 형식 건너뜜: {url}")
            continue

        data = None
        response = None
        current_headers = None
        is_naver_api = "openapi.naver.com/v1/search/news.json" in url

        if is_naver_api:
            if not naver_headers:
                print(f"⚠️ 네이버 API 키가 없어 '{url}' 수집 건너뜀니다.")
                continue
            print(f"🔎 네이버 뉴스 API 수집: {url}")
            current_headers = naver_headers
        elif "thenewsapi.com/v1/news/headlines" in url or "thenewsapi.com/v1/news/top" in url:
            print(f"🔎 thenewsapi.com API 수집: {url}")
        elif "gnews.io/api/v4" in url:
            print(f"🔎 gnews.io API 수집: {url}")
        else:
            print(f"❓ api_sources.txt의 알 수 없는 URL 형식 건너김: {url}")
            continue
        
        try:
            response = requests.get(url, headers=current_headers, timeout=10, verify=True)
            response.raise_for_status()
            data = response.json()

            items = []
            source_type = "Unknown API"

            if is_naver_api:
                items = data.get("items", [])
                source_type = "Naver News API"
            elif "thenewsapi.com" in url:
                items = data.get("data", [])
                source_type = "thenewsapi.com"
            elif "gnews.io" in url:
                items = data.get("articles", [])
                source_type = "gnews.io"

            if not items:
                print(f"⚠️ {source_type} 응답에 예상되는 기사 목록 키 또는 항목이 없습니다: {url}")
            else:
                print(f"✅ {source_type} 응답 항목 수: {len(items)}")

            count_added_from_url = 0
            for item in items:
                if isinstance(item, dict):
                    title = None
                    url_link = None
                    raw_summary = None
                    source_name = None
                    published_at = None
                    item_category = []

                    if source_type == "Naver News API":
                        title = item.get("title", "")
                        url_link = item.get("link")
                        raw_summary = item.get("description", "")
                        source_name = source_type
                        published_at = item.get('pubDate')
                    elif source_type == "thenewsapi.com":
                        title = item.get("title", "")
                        url_link = item.get("url")
                        raw_summary = item.get("snippet", "")
                        source_name = item.get("source", source_type)
                        published_at = item.get('published_at')
                    elif source_type == "gnews.io":
                        title = item.get("title", "")
                        url_link = item.get("url")
                        raw_summary = item.get("description", "")
                        source_info = item.get("source")
                        if isinstance(source_info, dict):
                            source_name = source_info.get("name", source_type)
                        else:
                            source_name = source_type
                        published_at = item.get('publishedAt')

                    cleaned_summary = html.unescape(raw_summary) if raw_summary else ""

                    if not title or not url_link:
                        print(f"⚠️ 필수 정보(제목 또는 URL) 누락으로 항목 건너뜀: {item}")
                        continue

                    article_for_pipeline = {
                        "title": title,
                        "url": url_link,
                        "summary": cleaned_summary,
                        "published_at": published_at,
                        "source": source_name,
                    }
                    if item_category:
                        article_for_pipeline["category"] = item_category

                    processed_item = process_and_store_article(article_for_pipeline)
                    articles.append(processed_item)
                    count_added_from_url += 1
                else:
                    print(f"⚠️ 스킵됨: API 응답 항목이 딕셔너리 형태가 아님 → {item}")
            print(f"✅ 수집 완료: {url} ({count_added_from_url}개 항목 추가)")

        except requests.exceptions.RequestException as e_req:
            print(f"❌ 요청 오류 ({url}): {e_req}")
        except json.JSONDecodeError as e_json:
            print(f"❌ JSON 파싱 오류 ({url}): {e_json}")
        except Exception as e_general:
            print(f"❌ 알 수 없는 오류 발생 ({url}): {e_general}")


    print(f"\n✅ API 수집 과정 완료. 총 {len(articles)}개 항목 수집 시도.")
    return articles


def collect_from_rss_file(filepath="rss_sources.txt"): #
    articles = []
    sources_dir = os.path.join(_project_root, "src", "sources")
    sources_filepath = os.path.join(sources_dir, filepath)
    print(f"✅ RSS 소스 파일 로드 시도: {sources_filepath}")

    urls = []
    try:
        with open(sources_filepath, "r", encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        print(f"✅ '{filepath}'에서 {len(urls)}개의 RSS 소스 URL 로드 완료")
    except FileNotFoundError:
        print(f"❌ 에러: RSS 소스 파일({sources_filepath})을 찾을 수 없습니다.")
        return articles
    except Exception as e:
        print(f"❌ 에러: RSS 소스 파일({sources_filepath})을 읽는 중 오류 발생: {e}")
        return articles


    print("\n🌐 RSS 수집 시작...")
    for url in urls:
        if not url:
            continue

        print(f"\n🔎 RSS 피드 파싱 시도: {url}")
        try:
            feed = feedparser.parse(url)

            if feed.bozo:
                print(f"⚠️ 경고: RSS 피드 파싱 중 문제 발생: {url} | {feed.bozo_exception}")
                if not isinstance(feed.bozo_exception, feedparser.CharacterEncodingOverride):
                    print(f"❌ 파싱 오류로 해당 피드 건너뜜: {url}")
                    continue
            
            if not feed.entries:
                print(f"ℹ️ 정보: {url} 피드에 항목이 없습니다.")
                continue

            print(f"✅ 피드 파싱 성공. 항목 수: {len(feed.entries)}")

            feed_articles_count = 0
            for entry in feed.entries:
                raw_title = entry.get('title', 'No Title Available')
                raw_description = entry.get('summary', entry.get('description', 'No Description Available'))
                item_url = entry.get('link', 'No URL Available')
                pub_date = entry.get('published', entry.get('updated', 'No Publish Date Available'))

                final_title = html.unescape(raw_title).strip() if raw_title else "No Title Available"
                if raw_description:
                     final_description = html.unescape(raw_description)
                else:
                     final_description = "No Description Available"
                
                if "news.google.com/news/rss" in url:
                    final_description = "Description not available from Google News RSS"


                item_category = []
                source_name = "Unknown RSS"

                if "biopharmadive.com" in url:
                    source_name = "BioPharma Dive RSS"
                elif "fiercebiotech.com" in url:
                    source_name = "FierceBiotech RSS"
                elif "endpts.com" in url:
                    source_name = "Endpoints News RSS"
                    if 'tags' in entry and isinstance(entry.tags, list):
                        item_category = [tag.get('term') for tag in entry.tags if tag.get('term')]
                    elif 'category' in entry and entry.get('category'):
                        item_category = [entry.get('category')]
                elif "hitnews.co.kr" in url:
                    source_name = "HitNews RSS"
                elif "news.google.com/news/rss" in url:
                    source_name = "Google News RSS"
                elif "biospace.com" in url:
                    source_name = "BioSpace RSS"
                elif "pharmaphorum.com" in url:
                    source_name = "Pharmaphorum RSS"
                elif "cafepharma.com" in url:
                    source_name = "CafePharma RSS"
                elif "biopharmatrend.com" in url:
                    source_name = "BioPharma Trend RSS"
                elif "biopharmaconsortium.com" in url:
                    source_name = "BioPharm Consortium RSS"

                if item_url == 'No URL Available':
                    print(f"⚠️ URL 정보 없는 RSS 항목 건너뜀: {final_title}")
                    continue
                
                article_for_pipeline = {
                    "title": final_title,
                    "url": item_url,
                    "summary": final_description,
                    "published_at": pub_date,
                    "source": source_name,
                }
                if item_category:
                    article_for_pipeline["category"] = item_category

                processed_item = process_and_store_article(article_for_pipeline)
                articles.append(processed_item)
                feed_articles_count += 1
            print(f"✅ {source_name} 항목 {feed_articles_count}개 수집 완료 (총 누적 {len(articles)}개)")
        except Exception as e_fp:
            print(f"❌ RSS 피드 처리 중 오류 발생 ({url}): {e_fp}")


    print(f"\n✅ 전체 RSS 수집 완료. 총 {len(articles)}개 항목 수집 시도.")
    return articles


def collect_from_dart_api():
    disclosures = []
    if not DART_API_KEY:
        print("❌ 오류: DART_API_KEY가 설정되지 않았습니다. config.yaml 파일을 확인하세요.")
        return disclosures

    end_date = datetime.today()
    start_date = end_date - timedelta(days=89)

    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "bgn_de": start_date.strftime("%Y%m%d"),
        "end_de": end_date.strftime("%Y%m%d"),
        "page_no": 1,
        "page_count": 100
    }

    print("\n🌐 DART API 수집 시작...")
    try:
        response = requests.get(url, params=params, timeout=10, verify=True)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "013":
            print("❌ DART API 오류: 인증키가 유효하지 않습니다. DART_API_KEY를 확인하세요.")
            return []
        elif data.get("status") != "000":
            print(f"❌ DART API 오류 발생: {data.get('message', '알 수 없는 오류')}")
            return []

        raw_list = data.get("list", [])
        print(f"✅ DART API 응답 항목 수: {len(raw_list)}개")

        for entry in raw_list:
            disclosure_summary = f"{entry.get('rcept_dt', '')} 접수된 공시: {entry.get('flr_nm', '제출인 불명')}"
            article_for_pipeline = {
                "title": f"[{entry.get('corp_name', '회사명 없음')}] {entry.get('report_nm', '보고서명 없음')}",
                "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={entry.get('rcept_no', '')}",
                "summary": disclosure_summary,
                "published_at": entry.get("rcept_dt"),
                "source": "DART"
            }
            if not entry.get('rcept_no'):
                print(f"⚠️ DART 항목 건너뜀 (rcept_no 없음): {article_for_pipeline['title']}")
                continue

            processed_item = process_and_store_article(article_for_pipeline)
            disclosures.append(processed_item)
        print(f"✅ DART API 수집 완료. 총 {len(disclosures)}개 항목 수집 시도.")
    except requests.exceptions.RequestException as e_req:
        print(f"❌ DART API 요청 오류: {e_req}")
    except json.JSONDecodeError as e_json:
        print(f"❌ DART API JSON 파싱 오류: {e_json}")
    except Exception as e_general:
        print(f"❌ DART API 처리 중 알 수 없는 오류: {e_general}")

    return disclosures


def collect_all_data():
    all_collected_items = []

    print("\n--- API 데이터 수집 시작 ---")
    api_data = collect_from_api_file()
    all_collected_items.extend(api_data)

    print("\n--- RSS 데이터 수집 시작 ---")
    rss_data = collect_from_rss_file()
    all_collected_items.extend(rss_data)

    print("\n--- DART 데이터 수집 시작 ---")
    dart_data = collect_from_dart_api()
    all_collected_items.extend(dart_data)

    print(f"\n--- 전체 데이터 수집 완료. 총 {len(all_collected_items)}개 항목 처리 시도 ---")
    return all_collected_items

if __name__ == "__main__":
    print("--- 뉴스 및 공시 데이터 수집 시작 (Celery 파이프라인으로 전달) ---")
    collected_data = collect_all_data()
    print("\n--- 수집 완료. Celery 워커가 태스크를 처리합니다. ---")
