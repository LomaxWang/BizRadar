from __future__ import annotations

import random
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from plugins.base_scraper import BaseScraper
    from config.settings import Settings

# Registry dict mapping name -> scraper class
SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {}


def register_scraper(name: str, cls: type[BaseScraper]) -> None:
    """Register a scraper class under the given name."""
    SCRAPER_REGISTRY[name] = cls


def _load_all() -> None:
    """延迟加载并注册所有插件（避免循环导入）。"""
    from plugins.v2ex_scraper import V2EXScraper
    from plugins.hackernews_scraper import HackerNewsScraper
    from plugins.reddit_scraper import RedditScraper
    from plugins.xhs_scraper import XhsScraper
    from plugins.zhihu_scraper import ZhihuScraper
    from plugins.producthunt_scraper import ProductHuntScraper
    from plugins.indiehackers_scraper import IndieHackersScraper
    from plugins.appstore_scraper import AppStoreScraper
    from plugins.sspai_scraper import SspaiScraper
    from plugins.kr36_scraper import Kr36Scraper
    from plugins.twitter_scraper import TwitterScraper
    from plugins.weibo_scraper import WeiboScraper

    for cls in (
        V2EXScraper, HackerNewsScraper, RedditScraper,
        XhsScraper, ZhihuScraper,
        ProductHuntScraper, IndieHackersScraper, AppStoreScraper,
        SspaiScraper, Kr36Scraper, TwitterScraper, WeiboScraper,
    ):
        if cls.name not in SCRAPER_REGISTRY:
            SCRAPER_REGISTRY[cls.name] = cls


def get_scraper(name: str, settings: Optional["Settings"] = None) -> "BaseScraper":
    """Instantiate and return a scraper by name, transparently passing settings.

    从 settings 自动透传：
      - multi_hop / max_comments
      - hot_enabled / hot_nodes_enabled / hot_min_points
    Raises ValueError for unknown names.
    """
    if not SCRAPER_REGISTRY:
        _load_all()

    key = name.strip().lower()
    if key not in SCRAPER_REGISTRY:
        raise ValueError(f"Unknown source: {name!r}. Available: {sorted(SCRAPER_REGISTRY)}")
    cls = SCRAPER_REGISTRY[key]

    if settings is None:
        return cls()

    kwargs: dict = {
        "multi_hop": settings.multi_hop_enabled,
        "max_comments": settings.multi_hop_max_comments,
    }
    # 按插件差异化注入 hot / serper_key 参数
    cls_name = cls.__name__
    if cls_name == "V2EXScraper":
        kwargs["hot_nodes_enabled"] = settings.hot_mode_enabled
    elif cls_name == "HackerNewsScraper":
        kwargs["hot_enabled"] = settings.hot_mode_enabled
        kwargs["hot_min_points"] = settings.hn_hot_min_points
    elif cls_name == "RedditScraper":
        kwargs["hot_enabled"] = settings.hot_mode_enabled
    elif cls_name in ("ProductHuntScraper", "IndieHackersScraper", "Kr36Scraper"):
        kwargs["serper_api_key"] = settings.serper_api_key or None

    try:
        return cls(**kwargs)
    except TypeError:
        # 参数不兼容时静默 fallback（向后兼容）
        return cls()


def list_sources() -> list[str]:
    """返回所有已注册数据源名称。"""
    if not SCRAPER_REGISTRY:
        _load_all()
    return sorted(SCRAPER_REGISTRY.keys())


def pick_search_keywords(settings: "Settings") -> list[str]:
    """从关键词池中随机抽取本轮搜索关键词。"""
    pool = settings.keyword_pool
    if not pool:
        return []
    n = min(settings.keywords_per_run, len(pool))
    return random.sample(pool, n)
