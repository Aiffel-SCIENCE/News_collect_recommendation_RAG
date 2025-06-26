# test_push_article.py

import redis
import json

# Redis 연결 (도커에서 Redis를 6379 포트로 노출한 상태여야 함)
r = redis.Redis(host="localhost", port=6379, db=0)

sample_article = {
    "url": "https://www.hani.co.kr/arti/society/health/1118066.html",
    "title": "수면 부족, 뇌 질환 위험 높인다",
    "content": "",  # processor에서 본문이 채워질 예정
    "summary": "",
    "published_at": "",
    "source": "hani"
}

# Redis 큐에 넣기
r.lpush("raw_articles", json.dumps(sample_article))
print("✅ 테스트 기사 Redis의 'raw_articles' 큐에 추가 완료!")
