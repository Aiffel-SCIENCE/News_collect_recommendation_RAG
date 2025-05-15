import feedparser

def collect_from_rss_file(filepath):
    articles = []

    with open(filepath, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                articles.append({
                    "title": entry.title,
                    "url": entry.link,
                    "summary": entry.get("summary", ""),
                    "source": "RSS"
                })
        except Exception as e:
            print(f"❌ RSS 수집 실패: {url} | {e}")
    
    return articles
