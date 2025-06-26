from src.processor.processor import preprocessor

test_json = '''{
    "id": "uuid",
    "title": "기사 제목",
    "content": "기사 내용, abcd 1234 가나다라 !@#$%^&*()",
    "url": "https://news.example.com/article",
    "published_at": "2025-05-20T12:34:56",
    "embedding": [0.12, -0.98],
    "summary": "요약된 내용",
    "source": "naver",
    "checked": true
}'''

result = preprocessor(test_json)

print(result)
