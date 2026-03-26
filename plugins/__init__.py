from plugins.base_scraper import BaseScraper, RawItem
from plugins.hackernews_scraper import HackerNewsScraper
from plugins.reddit_scraper import RedditScraper
from plugins.registry import get_scraper, register_scraper
from plugins.v2ex_scraper import V2EXScraper

# Register all built-in scrapers
register_scraper("v2ex", V2EXScraper)
register_scraper("hackernews", HackerNewsScraper)
register_scraper("reddit", RedditScraper)

__all__ = [
    "BaseScraper",
    "RawItem",
    "V2EXScraper",
    "HackerNewsScraper",
    "RedditScraper",
    "get_scraper",
    "register_scraper",
]
