# tests/main_test.py

import logging
import threading
import time
import subprocess
import requests
import json

import urllib3
from urllib3.exceptions import HeaderParsingError
urllib3.disable_warnings(HeaderParsingError)

from src.news_collector.news_collector import collect_all_data
from src.pre_checker.pre_checker import run_pre_checker_step
from src.filter1.filter1 import filter_article_unit as apply_filter1
from src.filter2.filter2 import filter_article_unit as apply_filter2
from src.processor.processor import process_article_unit as extract_article_content
from src.embedding.embedding import process_article_unit as generate_article_embedding
from src.config_loader.redis import r as redis_manager

logging.basicConfig(level=logging.INFO)

def run_pipeline():
    logging.info("🟢 STEP 1: 뉴스 수집")
    articles = collect_all_data()

    logging.info("🟢 STEP 2: 중복 제거 및 유효성 검사")
    run_pre_checker_step()

    # ✅ STEP 2.1: pre_checked MQ에 들어간 기사들을 다시 꺼내서 processed MQ로 보내기
    redis_manager.connect_client()
    while True:
        article = redis_manager.get_from_mq("pre_checked")
        if article is None:
            print("📭 pre_checked MQ가 비었습니다. 다음 단계로 진행합니다.")
            break
        else:
            print(f"✅ pre_checked → processed 로 전달: {article.get('title', '제목 없음')[:30]}...")
            redis_manager.send_to_mq("processed", article)

    # ✅ dart 기사 제외
    articles = [a for a in articles if "dart.fss.or.kr" not in a.get("url", "")]
    logging.info(f"🧹 dart 기사 제외됨 → 남은 기사 수: {len(articles)}")

    logging.info("🟢 STEP 2.5: 기사 본문(content) 추출 및 임베딩 시작")
    processed_articles = []
    for article in articles:
        article = extract_article_content(article)
        if article is None:
            print("⚠️ 본문 없음 → 기사 제외 (NoneType)")
            continue
        if not article.get("content"):
            print(f"⚠️ 본문 없음 → 기사 제외: {article.get('url')}")
            continue
        article = generate_article_embedding(article)
        processed_articles.append(article)

    print(f"⚠️ content 없음: {sum(1 for a in processed_articles if not a.get('content'))} / 전체: {len(processed_articles)}")

    if processed_articles:
        print("📌 예시 기사 구조:")
        print(json.dumps(processed_articles[0], indent=2, ensure_ascii=False))

    logging.info("🟢 STEP 3: 전처리 모듈에 기사 전달 (Redis MQ)")
    for article in processed_articles:
        redis_manager.send_to_mq("pre_checked", article)

    logging.info("🟢 STEP 4: Filter1 실행 및 Redis 직접 전달")
    passed_articles = []
    dropped_count = 0
    for article in processed_articles:
        result = apply_filter1(article)
        if result["checked"].get("filter1"):
            redis_manager.send_to_mq("filter1_passed", result)
            passed_articles.append(result)
            print(f"✅ Filter1 통과: {result['title'][:30]}...")
        else:
            dropped_count += 1
            print(f"🚫 Filter1 탈락: {result['title'][:30]}...")

    logging.info(f"✅ Filter1 통과 기사 수: {len(passed_articles)} / 탈락: {dropped_count}")
    if len(passed_articles) == 0:
        logging.warning("⚠️ Filter1 통과 기사가 없습니다. 필터 기준 또는 기사 content를 확인하세요.")

    logging.info("🟢 STEP 7: TF-IDF 기반 Filter2 실행")
    articles = [apply_filter2(article) for article in passed_articles]

    logging.info("🟢 STEP 8: Filter3 모듈 서브프로세스로 실행")
    try:
        subprocess.Popen(
            ["python", "-m", "src.filter3.filter3"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("🟢 Filter3 백그라운드 실행 완료. 다음 단계로 계속 진행합니다.")
    except Exception as e:
        print("❌ Filter3 실행 중 예외 발생:", e)

    logging.info("🟢 STEP 9: 임베딩 생성 (최종)")
    embedded_articles = [generate_article_embedding(article) for article in articles]

    logging.info("🟢 STEP 10: 쿼리 응답 (FastAPI 서버로 HTTP 요청)")
    query = "최근 mRNA 백신 동향"
    try:
        response = requests.post(
            "http://llm-api:8000/query",
            json={"query": query},
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            print(f"\n🧠 ✅ LLM 응답 결과:\n질문: {query}\n답변: {result.get('answer')}", flush=True)
        else:
            print("❌ LLM API 요청 실패:", response.status_code, response.text)
    except Exception as e:
        print("❌ LLM 요청 중 오류 발생:", e)

    logging.info("✅ 전체 통합 테스트 완료")

if __name__ == "__main__":
    run_pipeline()