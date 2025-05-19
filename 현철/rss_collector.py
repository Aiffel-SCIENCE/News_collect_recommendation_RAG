# 필요한 라이브러리 임포트
import feedparser
import os
import html # HTML 엔티티 디코딩을 위해 임포트 (태그 제거 후 사용할 수 있음)
from bs4 import BeautifulSoup # HTML 태그 제거를 위해 임포트

# RSS 피드 파일에서 URL을 읽어 데이터를 수집하는 함수
def collect_from_rss_file(filepath="rss_sources.txt"):
    articles = [] # 수집된 기사 데이터를 저장할 리스트

    # rss_sources.txt 파일 경로를 이 스크립트 파일 위치 기준이 아닌 프로젝트 루트 기준으로 찾습니다.
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 현재 파일 위치에서 두 단계 위로 이동
    sources_filepath = os.path.join(base_dir, filepath) # 프로젝트 루트에 있는 rss_sources.txt 경로

    print(f"✅ RSS 소스 파일 로드 시도: {sources_filepath}")

    # rss_sources.txt 파일에서 URL 목록 읽기
    urls = []
    try:
        with open(sources_filepath, "r", encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        print(f"✅ '{filepath}'에서 {len(urls)}개의 RSS 소스 URL 로드 완료")
    except FileNotFoundError:
        print(f"❌ 오류: RSS 소스 파일 '{sources_filepath}' 을 찾을 수 없습니다.")
        return articles
    except Exception as e:
        print(f"❌ RSS 소스 파일 읽기 오류: {sources_filepath} | {e}")
        return articles

    # 로드된 각 URL을 처리하며 데이터 수집
    for url in urls:
        print(f"🔎 RSS 피드 파싱 시도: {url}")
        try:
            # feedparser를 사용하여 RSS 피드 파싱
            feed = feedparser.parse(url)

            # 파싱 중 오류가 있는지 확인
            if feed.bozo:
                print(f"⚠️ 오류: RSS 피드 파싱 중 문제 발생: {url} | {feed.bozo_exception}")
                continue

            print(f"✅ 피드 파싱 성공. 항목 수: {len(feed.entries)}")

            # --- 새로 추가된 BioPharma Dive URL 처리 로직 ---
            if "biopharmadive.com" in url:
                 print(f"✨ BioPharma Dive RSS 피드 ({len(feed.entries)} 항목) 처리 중...")
                 for entry in feed.entries:
                     # 제목과 설명에 포함된 HTML 태그 제거
                     raw_title = entry.get('title', 'No Title Available')
                     raw_description = entry.get('summary', 'No Description Available') # 설명/요약

                     # BeautifulSoup을 사용하여 HTML 태그 제거 및 텍스트 추출
                     soup_title = BeautifulSoup(raw_title, 'html.parser')
                     clean_title = soup_title.get_text()
                     final_title = html.unescape(clean_title) # HTML 엔티티 디코딩

                     soup_desc = BeautifulSoup(raw_description, 'html.parser')
                     clean_description = soup_desc.get_text()
                     final_description = html.unescape(clean_description) # HTML 엔티티 디코딩


                     item_data = {
                         "title": final_title,                                   # HTML 태그 제거된 제목
                         "url": entry.get('link', 'No URL Available'),           # URL
                         "description": final_description,                       # HTML 태그 제거된 설명
                         "pubDate": entry.get('published', 'No Publish Date Available'), # 발행일
                         # category는 요청 없었으므로 포함 안 함
                         "source": "BioPharma Dive RSS",                         # 소스 구분 명시
                     }
                     articles.append(item_data)
                 print(f"✅ BioPharma Dive 항목 {len(feed.entries)}개 수집 완료 (총 누적 {len(articles)}개)")


            # --- FierceBiotech URL 처리 로직 ---
            elif "fiercebiotech.com" in url:
                 print(f"✨ FierceBiotech RSS 피드 ({len(feed.entries)} 항목) 처리 중...")
                 for entry in feed.entries:
                     raw_title = entry.get('title', 'No Title Available')
                     soup = BeautifulSoup(raw_title, 'html.parser')
                     clean_title = soup.get_text()
                     final_title = html.unescape(clean_title)

                     item_data = {
                         "title": final_title,
                         "url": entry.get('link', 'No URL Available'),
                         "description": entry.get('summary', 'No Description Available'),
                         "pubDate": entry.get('published', 'No Publish Date Available'),
                         "source": "FierceBiotech RSS",
                     }
                     articles.append(item_data)
                 print(f"✅ FierceBiotech 항목 {len(feed.entries)}개 수집 완료 (총 누적 {len(articles)}개)")


            # --- Endpoints News URL 처리 로직 ---
            elif "endpts.com" in url:
                print(f"✨ Endpoints News RSS 피드 ({len(feed.entries)} 항목) 처리 중...")
                for entry in feed.entries:
                    entry_categories = []
                    if 'tags' in entry and isinstance(entry.tags, list):
                        entry_categories = [tag.get('term') for tag in entry.tags if tag.get('term')]
                    elif 'category' in entry:
                         entry_categories = [entry.get('category')] if entry.get('category') else []

                    item_data = {
                        "title": entry.get('title', 'No Title Available'),
                        "url": entry.get('link', 'No URL Available'),
                        "description": entry.get('summary', 'No Description Available'),
                        "pubDate": entry.get('published', 'No Publish Date Available'),
                        "category": entry_categories,
                        "source": "Endpoints News RSS",
                    }
                    articles.append(item_data)
                print(f"✅ Endpoints News 항목 {len(feed.entries)}개 수집 완료 (총 누적 {len(articles)}개)")

            # --- HitNews URL 처리 로직 ---
            elif "hitnews.co.kr" in url:
                print(f"✨ HitNews RSS 피드 ({len(feed.entries)} 항목) 처리 중...")
                for entry in feed.entries:
                    item_data = {
                        "title": entry.get('title', 'No Title Available'),
                        "url": entry.get('link', 'No URL Available'),
                        "description": entry.get('summary', 'No Description Available'),
                        "pubDate": entry.get('published', 'No Publish Date Available'),
                        "source": "HitNews RSS",
                    }
                    articles.append(item_data)
                print(f"✅ HitNews 항목 {len(feed.entries)}개 수집 완료 (총 누적 {len(articles)}개)")

            # --- Google News URL 처리 로직 ---
            elif "news.google.com/news/rss" in url:
                print(f"✨ Google News RSS 피드 ({len(feed.entries)} 항목) 처리 중...")
                for entry in feed.entries:
                    item_data = {
                        "title": entry.get('title', 'No Title Available'),
                        "url": entry.get('link', 'No URL Available'),
                        # "description":는 Google News에서 제외
                        "pubDate": entry.get('published', 'No Publish Date Available'),
                        "source": "Google News RSS",
                    }
                    articles.append(item_data)
                print(f"✅ Google News 항목 {len(feed.entries)}개 수집 완료 (총 누적 {len(articles)}개)")

            # --- 알 수 없는 URL 처리 로직 ---
            else:
                print(f"❓ rss_sources.txt의 알 수 없는 RSS 피드 URL 형식 건너김: {url}")

        except Exception as e:
            print(f"❌ RSS 피드 처리 중 예상치 못한 오류: {url} | {e}")
            continue

    print(f"✅ 전체 RSS 수집 완료. 총 {len(articles)}개 항목 수집.")
    return articles
