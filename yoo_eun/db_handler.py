from pymongo import MongoClient
from dotenv import load_dotenv
import os
import certifi

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())

db = client["newsdb"]
collection = db["articles"]

def save_article(article):
    if not collection.find_one({"url": article["url"]}):
        collection.insert_one(article)
        print(f"✅ 저장됨: {article['title']}")
    else:
        print(f"⚠️ 중복: {article['title']}")