from collector.api_collector import collect_from_api_file
from db_handler import save_article
from checker.pre_checker import is_valid

api_articles = collect_from_api_file("api_sources.txt")

for article in api_articles:
    if is_valid(article):
        save_article(article)
