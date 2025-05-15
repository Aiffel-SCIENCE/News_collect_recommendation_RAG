import requests

def collect_from_api_file(filepath):
    articles = []

    with open(filepath, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            data = response.json()

            # News API나 Currents API 공통 처리 예시
            items = data.get("articles") or data.get("news") or []

            for item in items:
                articles.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "summary": item.get("description", "") or item.get("summary", ""),
                    "source": "API"
                })

        except Exception as e:
            print(f"❌ API 수집 실패: {url} | {e}")

    return articles

