from plugins.base_scraper import BaseScraper, RawItem
from plugins.hackernews_scraper import HackerNewsScraper
from plugins.reddit_scraper import RedditScraper
from plugins.registry import get_scraper, list_sources, register_scraper
from plugins.v2ex_scraper import V2EXScraper
from plugins.xhs_scraper import XhsScraper
from plugins.zhihu_scraper import ZhihuScraper

# 新数据源
from plugins.producthunt_scraper import ProductHuntScraper
from plugins.indiehackers_scraper import IndieHackersScraper
from plugins.appstore_scraper import AppStoreScraper
from plugins.sspai_scraper import SspaiScraper
from plugins.kr36_scraper import Kr36Scraper
from plugins.twitter_scraper import TwitterScraper
from plugins.weibo_scraper import WeiboScraper

# ── 注册所有内置数据源 ────────────────────────────────────────────────────────
# 原有数据源（5 个）
register_scraper("v2ex", V2EXScraper)
register_scraper("hackernews", HackerNewsScraper)
register_scraper("reddit", RedditScraper)
register_scraper("xhs", XhsScraper)
register_scraper("xiaohongshu", XhsScraper)  # alias
register_scraper("zhihu", ZhihuScraper)

# 新数据源（7 个）
register_scraper("producthunt", ProductHuntScraper)
register_scraper("indiehackers", IndieHackersScraper)
register_scraper("appstore", AppStoreScraper)
register_scraper("sspai", SspaiScraper)
register_scraper("kr36", Kr36Scraper)          # 36氪 + 虎嗅
register_scraper("twitter", TwitterScraper)
register_scraper("weibo", WeiboScraper)

__all__ = [
    "BaseScraper",
    "RawItem",
    # 爬虫类
    "V2EXScraper",
    "HackerNewsScraper",
    "RedditScraper",
    "XhsScraper",
    "ZhihuScraper",
    "ProductHuntScraper",
    "IndieHackersScraper",
    "AppStoreScraper",
    "SspaiScraper",
    "Kr36Scraper",
    "TwitterScraper",
    "WeiboScraper",
    # 注册工具
    "get_scraper",
    "list_sources",
    "register_scraper",
]
