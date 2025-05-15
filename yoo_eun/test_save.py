from db_handler import save_article

dummy_article = {
    "title": "테스트 뉴스",
    "url": "https://example.com/test",
    "summary": "이것은 테스트 기사입니다.",
    "source": "API"
}

save_article(dummy_article)
