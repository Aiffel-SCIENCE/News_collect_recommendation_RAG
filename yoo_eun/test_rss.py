from collector.rss_collector import collect_from_rss_file
from db_handler import save_article
from checker.pre_checker import is_valid

rss_articles = collect_from_rss_file("rss_sources.txt")

for article in rss_articles:
    if is_valid(article):
        save_article(article)
