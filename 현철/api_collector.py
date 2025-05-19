import requests
import html # HTML 엔티티 디코딩을 위해 임포트
import os # naver.keys.txt, api_sources.txt 파일 경로 처리를 위해 임포트

# naver.keys.txt 파일에서 API 키를 읽어오는 함수
def load_naver_keys(filepath="naver.keys.txt"):
    naver_client_id = None
    naver_client_secret = None
    # naver.keys.txt 파일은 이 스크립트 파일 위치 기준이 아닌 프로젝트 루트 레벨에 있을 것입니다.
    # os.path.join과 os.path.dirname을 사용하여 스크립트 파일의 절대 경로를 기준으로 naver.keys.txt 파일 경로를 찾습니다.
    # __file__은 현재 스크립트(api_collector.py)의 경로를 나타냅니다.
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # collector 폴더를 거슬러 올라가 프로젝트 루트 찾기
    keys_filepath = os.path.join(base_dir, filepath) # 프로젝트 루트에 있는 naver.keys.txt 경로

    try:
        # 파일이 있는지 확인
        if not os.path.exists(keys_filepath):
             print(f"❌ 오류: Naver keys 파일 '{keys_filepath}' 을 찾을 수 없습니다.")
             return None, None

        # 파일을 열 때 인코딩을 명시적으로 지정 (Windows cp949 오류 방지)
        with open(keys_filepath, "r", encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 'key=value' 형태의 유효한 줄이고 주석(#)이 아닌 경우 파싱
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1) # 첫번째 = 기준으로 분리
                    if key.strip() == "client_id": # naver.keys.txt의 실제 키 이름 사용 (공백 제거)
                        naver_client_id = value.strip() # 값의 공백 제거
                    elif key.strip() == "client_secret": # naver.keys.txt의 실제 키 이름 사용 (공백 제거)
                        naver_client_secret = value.strip() # 값의 공백 제거

        if not naver_client_id or not naver_client_secret:
             print(f"❌ 오류: '{filepath}' 파일에서 client_id 또는 client_secret 값을 읽어오지 못했습니다. 파일 내용을 확인하세요.")
             return None, None

        print(f"✅ 네이버 API 키 로드 성공") # 키 로드 성공 확인

        return naver_client_id, naver_client_secret

    except Exception as e:
        print(f"❌ Naver keys 파일 읽기 오류: {e}")
        return None, None


# API 소스 파일에서 URL을 읽어 데이터를 수집하는 메인 함수
# 이 함수는 main.py에서 호출됩니다.
def collect_from_api_file(filepath="api_sources.txt"): # 기본 파일 경로 설정
    articles = []
    # api_sources.txt 파일 경로를 이 스크립트 파일 위치 기준이 아닌 프로젝트 루트 기준으로 찾습니다.
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 프로젝트 루트 폴더
    sources_filepath = os.path.join(base_dir, filepath) # 프로젝트 루트에 있는 api_sources.txt 경로

    # 네이버 API 키 로드
    print("✅ 네이버 API 키 로드 시도...")
    naver_client_id, naver_client_secret = load_naver_keys()

    # 네이버 API 키가 제대로 로드되지 않았으면 수집 진행 안 함
    if not naver_client_id or not naver_client_secret:
        print("❌ 네이버 API 키가 없어 API 수집을 진행할 수 없습니다.")
        return articles # 빈 리스트 반환

    # 네이버 API 호출에 필요한 헤더 설정
    headers = {
        "X-Naver-Client-Id": naver_client_id,
        "X-Naver-Client-Secret": naver_client_secret
    }

    # api_sources.txt 파일에서 URL 목록 읽기
    try:
        # 파일을 열 때 인코딩을 명시적으로 지정 (Windows cp949 오류 방지)
        with open(sources_filepath, "r", encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ 오류: API 소스 파일 '{sources_filepath}' 을 찾을 수 없습니다.")
        return articles # 파일 없으면 빈 리스트 반환
    except Exception as e:
         print(f"❌ API 소스 파일 읽기 오류: {sources_filepath} | {e}")
         return articles # 오류 시 빈 리스트 반환

    print(f"✅ '{filepath}'에서 {len(urls)}개의 API 소스 URL 로드 완료") # 로드된 URL 수 확인


    for url in urls:
        # URL이 네이버 뉴스 API URL인지 확인 (api_sources.txt에 다른 API도 있다면 구분)
        if "openapi.naver.com/v1/search/news.json" in url:
            print(f"🔎 네이버 뉴스 API 수집: {url}")
            try:
                # headers 파라미터 추가하여 API 호출
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status() # HTTP 오류 발생 시 예외 발생 (4xx, 5xx 등)

                data = response.json()

                # 네이버 뉴스 API 응답은 'items' 리스트 안에 각 기사 정보가 있습니다.
                items = data.get("items", [])

                if not items:
                    print(f"⚠️ 네이버 API 응답에 'items' 결과가 없습니다: {url}") # 결과 없을 경우 메시지
                else:
                     print(f"✅ 네이버 API 응답 항목 수: {len(items)}") # 응답받은 항목 수 출력


                for item in items:
                    # 네이버 API 응답 필드와 저장할 필드 매핑
                    # 네이버 API 응답 필드: title, originallink, link, description, pubDate
                    title = html.unescape(item.get("title", "")) # HTML 엔티티 디코딩
                    link = item.get("link") # 네이버 뉴스 URL
                    # originallink = html.unescape(item.get("originallink", "")) # 원문 URL (필요시 사용)
                    summary = html.unescape(item.get("description", "")) # HTML 엔티티 디코딩
                    # pubDate_str = item.get("pubDate") # 발행일 (필요시 파싱하여 저장)

                    # 필수 필드가 있는지 간단히 확인 (제목, 링크, 요약)
                    if not title or not link or not summary:
                         print(f"⚠️ 불완전한 네이버 API 응답 항목 건너옴 (필수 필드 누락): {item.get('title', '제목 없음')[:50]}...")
                         continue # 불완전한 항목은 건너뛰기

                    # 저장할 항목 형식에 맞춰 딕셔너리 생성 (main.py와 db_handler.py에서 사용하는 형식)
                    articles.append({
                        "title": title,
                        "url": link, # 네이버 뉴스 URL을 저장 (중복 확인 키로 사용될 가능성 높음)
                        "summary": summary,
                        "source": "Naver News API", # 소스 구분
                        # "originallink": originallink, # 원문 링크도 저장 가능 (필요시)
                        # "pubDate": pubDate_str # 날짜도 저장 가능 (필요시)
                    })

                # 이 시점의 articles 길이는 누적된 전체 수집 항목 수입니다.
                # print(f"✅ 네이버 API 수집 완료: {url} ({len(articles)}개 항목 추가)") # 수집 항목 수 출력 (누적)

            except requests.exceptions.RequestException as req_e:
                print(f"❌ 네이버 API 요청 오류: {url} | {req_e}")
                if req_e.response is not None:
                     print(f"    HTTP 상태 코드: {req_e.response.status_code}") # HTTP 오류 코드 출력
                     print(f"    응답 내용: {req_e.response.text[:200]}...") # 응답 내용 일부 출력
            except ValueError: # JSON 파싱 오류
                 print(f"❌ 네이버 API 응답 JSON 파싱 오류: {url} | 응답 내용이 JSON 형식이 아닙니다.")
            except Exception as e:
                print(f"❌ API 수집 중 예상치 못한 오류: {url} | {e}")

        # elif "다른 API URL 패턴" in url:
        #     # api_sources.txt에 다른 API가 있다면 여기에 해당 수집 로직 추가
        #     pass
        else:
             # 네이버 뉴스 API URL도 아니고 다른 처리할 API도 아닌 경우
             print(f"❓ api_sources.txt의 알 수 없는 URL 형식 건너김: {url}")


    print(f"✅ API 수집 완료. 총 {len(articles)}개 항목 수집.")
    return articles
