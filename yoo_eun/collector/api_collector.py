import requests
import html # HTML 엔티티 디코딩을 위해 임포트
import os # keys, sources 파일 경로 처리를 위해 임포트
from bs4 import BeautifulSoup # HTML 태그 제거를 위해 임포트 (BeautifulSoup 설치 필요: pip install beautifulsoup4)
import json # 디버깅 시 JSON 출력에 사용될 수 있습니다.



def load_naver_keys(filepath="naver.keys.txt"):
    """ naver.keys.txt 파일에서 네이버 API 키(client_id, client_secret)를 읽어옵니다. """
    naver_client_id = None
    naver_client_secret = None
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # collector 폴더를 거슬러 올라가 프로젝트 루트 찾기
    keys_filepath = os.path.join(base_dir, filepath) # naver.keys.txt 파일 경로

    try:
        if not os.path.exists(keys_filepath):
            print(f"❌ 오류: Naver keys 파일 '{keys_filepath}' 을 찾을 수 없습니다.")
            return None, None

        with open(keys_filepath, "r", encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    if key.strip() == "client_id":
                        naver_client_id = value.strip()
                    elif key.strip() == "client_secret":
                        naver_client_secret = value.strip()

        if not naver_client_id or not naver_client_secret:
            print(f"❌ 오류: '{filepath}' 파일에서 client_id 또는 client_secret 값을 읽어오지 못했습니다. 파일 내용을 확인하세요.")
            return None, None

        print(f"✅ 네이버 API 키 로드 성공")

        return naver_client_id, naver_client_secret

    except Exception as e:
        print(f"❌ Naver keys 파일 읽기 오류: {e}")
        return None, None



# --- HTML 태그 제거 함수 ---
def strip_html_tags(text):
    """ BeautifulSoup을 사용하여 텍스트에서 HTML 태그를 제거하고 순수 텍스트를 반환합니다. """
    if not text:
        return ""
    try:
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        # print(f"⚠️ 오류: HTML 파싱 중 오류 발생 | {e}") # 디버깅용
        return text


# --- API 소스 파일에서 URL을 읽어 데이터를 수집하는 메인 함수 ---
def collect_from_api_file(filepath="api_sources.txt"):
    """
    api_sources.txt 파일에 나열된 URL에서 API 데이터를 수집합니다.
    URL 패턴에 따라 네이버, thenewsapi.com, gnews.io 등을 구분하여 처리합니다.
    thenewsapi.com과 gnews.io 키는 URL에 포함되어 있다고 가정합니다.
    """
    articles = []
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 프로젝트 루트 폴더
    sources_filepath = os.path.join(base_dir, filepath) # api_sources.txt 파일 경로

    # --- 필요한 API Key 로드 (수집 시작 전 미리 로드) ---
    print("✅ API 키 로드 시도...")

    naver_client_id, naver_client_secret = load_naver_keys()
    naver_headers = None
    if naver_client_id and naver_client_secret:
        naver_headers = {
            "X-Naver-Client-Id": naver_client_id,
            "X-Naver-Client-Secret": naver_client_secret
        }
    else:
        print("⚠️ 네이버 API 키가 없어 네이버 API 수집 시도 시 실패할 수 있습니다.")



    # api_sources.txt 파일에서 URL 목록 읽기
    urls = [] # URL 리스트 초기화
    print(f"✅ '{filepath}'에서 API 소스 URL 로드 시도...") # 파일 로드 시도 메시지
    try:
        with open(sources_filepath, "r", encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        print(f"✅ '{filepath}'에서 {len(urls)}개의 API 소스 URL 로드 완료") # 로드된 URL 수 확인
    except FileNotFoundError:
        print(f"❌ 오류: API 소스 파일 '{sources_filepath}' 을 찾을 수 없습니다.")
        return articles # 파일 없으면 빈 리스트 반환
    except Exception as e:
        print(f"❌ API 소스 파일 읽기 오류: {sources_filepath} | {e}")
        return articles # 오류 시 빈 리스트 반환


    # --- URL 목록 순회하며 수집 시작 ---
    print("\n🌐 API 수집 시작...")
    total_items_collected = 0 # 전체 수집된 항목 개수 카운터

    for url in urls:
        if not url.startswith('http'): # 유효한 URL 형식인지 간단히 확인
            print(f"⚠️ 유효하지 않은 URL 형식 건너뜀: {url}")
            continue

        # --- URL 패턴에 따라 API 구분 및 처리 ---

        # 기본 응답 데이터 변수 초기화
        data = None
        response = None # 응답 객체 초기화

        try:
            # 1. URL이 네이버 뉴스 API인 경우
            if "openapi.naver.com/v1/search/news.json" in url:
                if not naver_headers: # 네이버 키 없으면 건너뛰기
                    print(f"⚠️ 네이버 API 키가 없어 '{url}' 수집 건너뜁니다.")
                    continue

                print(f"🔎 네이버 뉴스 API 수집: {url}")
                # 네이버 API 호출 시 headers 필요
                response = requests.get(url, headers=naver_headers, timeout=10)

            # 2. URL이 thenewsapi.com인 경우 (키는 URL에 포함 가정)
            elif "thenewsapi.com/v1/news/headlines" in url or "thenewsapi.com/v1/news/top" in url:
                print(f"🔎 thenewsapi.com API 수집: {url}")
                response = requests.get(url, timeout=10)

            # 3. URL이 gnews.io인 경우 (키는 URL에 포함 가정)
            elif "gnews.io/api/v4" in url:

                print(f"🔎 gnews.io API 수집: {url}")
                # URL에 키가 포함되어 있다고 가정하고 URL만 가지고 GET 요청
                response = requests.get(url, timeout=10)

            # 4. 위에 정의된 어떤 API 패턴과도 일치하지 않는 URL인 경우
            else:
                # api_sources.txt에 나열되었지만 알려진 패턴(네이버, thenewsapi.com, gnews.io)이 아닌 경우
                print(f"❓ api_sources.txt의 알 수 없는 URL 형식 건너김: {url}")
                continue # 알 수 없는 URL은 여기서 건너뜁니다.


            # --- API 호출 성공 및 응답 처리 (위에서 response 객체가 성공적으로 생성된 경우) ---
            if response is not None:
                # HTTP 오류 발생 시 예외 발생
                response.raise_for_status()

                # 응답을 JSON 형식으로 파싱
                data = response.json()

                items = [] # 기사 항목 리스트 초기화
                source_type = "Unknown API" # 소스 타입 초기화

                # --- API 응답 구조에 맞춰 항목 리스트(items) 찾기 ---
                if "openapi.naver.com" in url:
                    items = data.get("items", []) # 네이버 응답은 'items' 키 사용
                    source_type = "Naver News API"
                elif "thenewsapi.com" in url:
                    items = data.get("data", []) # thenewsapi.com 응답은 'data' 키 사용
                    source_type = "thenewsapi.com"
                elif "gnews.io" in url:
                    items = data.get("articles", []) # gnews.io 응답은 'articles' 키 사용
                    source_type = "gnews.io"
                # else: items는 빈 리스트로 유지

                if not items:
                    print(f"⚠️ {source_type} 응답에 예상되는 기사 목록 키 또는 항목이 없습니다: {url}")

                else:
                    print(f"✅ {source_type} 응답 항목 수: {len(items)}")


                # --- 항목 리스트(items) 순회하며 데이터 추출 및 정리 ---
                count_added_from_url = 0 # 이 URL에서 실제로 추가된 항목 수 카운터
                for item in items:
                    if isinstance(item, dict): # 항목이 딕셔너리 형태인지 확인

                        # 각 API 응답 구조에 맞춰 필드 추출
                        title = None
                        url_link = None
                        raw_summary = None
                        source_name = None
                        # published_at = None # 발행일 필드 (필요시)

                        if source_type == "Naver News API":
                            title = item.get("title", "")
                            url_link = item.get("link") # 네이버는 'link' 필드
                            raw_summary = item.get("description", "") # 네이버는 'description' 필드
                            # 네이버 출처는 title에 포함되거나 별도 source 필드 없음 (혹은 originallink의 도메인)
                            # 여기서는 소스 타입 이름 사용
                            source_name = source_type
                            # published_at = item.get('pubDate') # 필요시 추가

                        elif source_type == "thenewsapi.com":
                            title = item.get("title", "")
                            url_link = item.get("url") # thenewsapi.com은 'url' 필드
                            raw_summary = item.get("snippet", "") # thenewsapi.com은 'snippet' 필드
                            source_name = item.get("source", source_type) # thenewsapi.com은 'source' 필드 (도메인)
                            # published_at = item.get('published_at') # 필요시 추가

                        elif source_type == "gnews.io":
                            title = item.get("title", "")
                            url_link = item.get("url") # gnews.io는 'url' 필드
                            raw_summary = item.get("description", "") # gnews.io는 'description' 필드
                            # gnews.io 출처는 'source' 필드인데, { 'name': '...' } 딕셔너리 형태
                            source_info = item.get("source")
                            if isinstance(source_info, dict):
                                source_name = source_info.get("name", source_type)
                            else:
                                source_name = source_type # 딕셔너리 형태가 아니면 소스 타입 이름 사용
                            # published_at = item.get('publishedAt') # 필요시 추가

                        # else: Unknown API -> 필드 추출 안 됨 (위에서 걸러지지만)

                        # --- 추출된 데이터 정리 및 검증 ---

                        # HTML 엔티티 디코딩 및 태그 제거 (summary/description/snippet에서)
                        plain_text_summary = strip_html_tags(html.unescape(raw_summary)) # 안전하게 unescape 후 태그 제거


                        # 필수 필드(title, url, summary)가 있는지 최종 확인
                        if not title or not url_link or not plain_text_summary:
                            # print(f"⚠️ 불완전한 항목 (필수 필드 누락) 건너뜀: {item.get('title', '제목 없음')[:50]}...") # 디버깅용
                            continue # 불완전한 항목은 저장하지 않음


                        # --- 항목 추가 ---
                        articles.append({
                            "title": title,
                            "url": url_link,
                            "summary": plain_text_summary, # HTML 제거된 summary 사용
                            "source": source_name, # 추출/정리된 출처 이름 사용
                            # "published_at": published_at # 발행일 (필요시 추가)
                        })
                        count_added_from_url += 1 # 이 URL에서 실제로 추가된 항목 수 카운트

                    else:
                        print(f"⚠️ 스킵됨: API 응답 항목이 딕셔너리 형태가 아님 → {item}") # 항목 형태 오류 메시지

                print(f"✅ 수집 완료: {url} ({count_added_from_url}개 항목 추가)") # 이 URL 처리 결과 요약

            # --- 오류 처리 ---
        except requests.exceptions.RequestException as req_e:
                # requests 라이브러리에서 발생하는 HTTP 오류, 연결 오류 등 처리
                print(f"❌ API 요청 오류: {url} | {req_e}")
                if req_e.response is not None:
                    print(f"    HTTP 상태 코드: {req_e.response.status_code}")
                    # 응답 내용이 너무 길면 잘라서 출력
                    try:
                        print(f"    응답 내용: {req_e.response.text[:500]}...") # 최대 500자 출력
                    except Exception:
                        print("    응답 내용 확인 불가")

        except ValueError as json_e:
                # response.json()에서 발생하는 오류 (응답 내용이 JSON 형식이 아닐 때) 처리
                print(f"❌ API 응답 JSON 파싱 오류: {url} | 응답 내용이 JSON 형식이 아닙니다: {json_e}")


        except Exception as e:
                # 위에 정의되지 않은 모든 예상치 못한 오류 처리
                print(f"❌ API 수집 중 예상치 못한 오류: {url} | {e}")


    # --- 전체 수집 과정 완료 ---
    print(f"\n✅ API 수집 과정 완료. 총 {len(articles)}개 항목 수집.")
    return articles

# 스크립트를 직접 실행할 때 main 함수 호출
if __name__ == "__main__":
    # 수집 함수 실행
    collected_data = collect_from_api_file()

    # 수집된 데이터를 필요에 따라 처리 (예: 출력, 파일 저장 등)
    print("\n--- 수집된 기사 데이터 확인 (일부) ---")
    # 처음 5개 항목만 출력
    for i, article in enumerate(collected_data[:5]):
        print(f"--- 항목 {i+1} ---")
        print(f"제목: {article.get('title', 'N/A')}")
        print(f"URL: {article.get('url', 'N/A')}")
        print(f"요약: {article.get('summary', 'N/A')[:200]}...") # 요약이 길 수 있으니 일부만 출력
        print(f"출처: {article.get('source', 'N/A')}")
        print("-" * 30)

    print(f"\n총 {len(collected_data)}개의 항목이 수집되었습니다.")
