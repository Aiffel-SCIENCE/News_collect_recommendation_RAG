import requests

def collect_from_api_file(filepath):
    articles = []

    with open(filepath, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            data = response.json()

            # ✅ 자동 응답 구조 파악
            if isinstance(data, dict):
                if "results" in data:
                    items = data["results"]
                elif "data" in data:
                    items = data["data"]
                elif "articles" in data:
                    items = data["articles"]
                elif "news" in data:
                    items = data["news"]
                else:
                    items = []
            else:
                items = []

            print(f"📥 {url} → 기사 개수: {len(items)}")

            for item in items:
                if isinstance(item, dict):  # ❗방어적 처리
                    source = item.get("source")
                    articles.append({
                        "title": item.get("title"),
                        "url": item.get("url") or item.get("link"),
                        "summary": item.get("description") or item.get("content") or "",
                        "published_at": item.get("pubDate") or item.get("publishedAt") or "",
                        "source": source.get("name") if isinstance(source, dict) else (source or "API")
                    })
                else:
                    print(f"⚠️ 스킵됨: item이 dict 아님 → {item}")

        except Exception as e:
            print(f"❌ API 수집 실패: {url} | {e}")

    return articles




