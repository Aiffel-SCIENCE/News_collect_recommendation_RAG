from collector.api_collector import collect_from_api_file
from collector.rss_collector import collect_from_rss_file
from collector.dart_collector import fetch_disclosures, format_disclosure
from db_handler import save_article
from checker.pre_checker import is_valid

def main():
    print("\n🚀 뉴스 & 공시 수집 시작")

    # 1. RSS 수집 (필요 시 주석 해제)
    print("\n📡 RSS 수집 중...")
    rss_articles = collect_from_rss_file("rss_sources.txt")
    print(f"🗂 RSS 기사 수: {len(rss_articles)}")

    # 2. API 수집
    print("\n🌐 API 수집 중...")
    api_articles = collect_from_api_file("api_sources.txt")
    print(f"🗂 API 기사 수: {len(api_articles)}")

    # 3. 공시(DART) 수집
    print("\n📄 공시 수집 중...")
    raw_disclosures = fetch_disclosures()
    dart_articles = [format_disclosure(d) for d in raw_disclosures]
    print(f"📦 공시 기사 수: {len(dart_articles)}")

    # 4. 통합 (원하면 rss_articles도 포함 가능)
    all_articles = rss_articles + api_articles + dart_articles
    print(f"\n📊 총 수집된 기사 수: {len(all_articles)}")

    # 5. 검사 및 저장
    for i, article in enumerate(all_articles):
        print(f"\n📰 [{article.get('source', 'N/A')}] {i+1}: {article['title'][:50]}...")
        if is_valid(article):
            save_article(article)
        else:
            print("⚠️ 유효하지 않아 저장 안 됨")

if __name__ == "__main__":
    main()



