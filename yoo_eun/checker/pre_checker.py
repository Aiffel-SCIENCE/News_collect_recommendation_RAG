def is_valid(article):
    # 제목이 비었거나 너무 짧으면 무시
    if not article.get("title") or len(article["title"]) < 5:
        return False
    return True