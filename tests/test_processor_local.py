import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from src.processor.processor import fetch_content_with_beautifulsoup

import requests
from bs4 import BeautifulSoup

url = "http://www.popcornnews.net/news/articleView.html?idxno=81826"
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.content, 'html.parser')

article_tag = soup.find("article", {"id": "article-view-content-div"})
if article_tag:
    text = article_tag.get_text(separator="\n", strip=True)
    print("✅ 추출 성공:")
    print(text[:500])  # 앞부분만 출력
else:
    print("❌ 추출 실패: article 태그를 찾을 수 없습니다.")

