from config import get_db

db = get_db()
collection = db["articles"]

def save_article(article: dict):
    # URL 중복 여부 확인
    if not collection.find_one({"url": article.get("url")}):
        collection.insert_one(article)
        print(f"✅ 저장됨: {article['title']}")
    else:
        print(f"⚠️ 중복: {article['title']}")
