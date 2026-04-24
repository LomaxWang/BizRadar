from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from plugins.base_scraper import BaseScraper, RawItem
from plugins.feed_utils import parse_feed

logger = logging.getLogger(__name__)

# 36氪多个频道 RSS
KR36_FEEDS = [
    ("https://36kr.com/feed", "36kr"),
    ("https://36kr.com/newsflashes/feed", "36kr_flash"),
]
# 虎嗅（多种备选 URL）
HUXIU_FEEDS = [
    ("https://www.huxiu.com/rss/", "huxiu"),
]

SERPER_URL = "https://google.serper.dev/search"
import os


class Kr36Scraper(BaseScraper):
    """36氪 + 虎嗅 聚合爬虫。

    两个平台均为中文科技媒体，文章聚焦创业/行业趋势，
    「融资」「创业」「解决了什么问题」类文章是痛点宝库。
    无需任何 Key，额外 Search 轨需要 SERPER_API_KEY。
    """

    name = "kr36"

    def __init__(
        self,
        *,
        include_huxiu: bool = True,
        include_serper: bool = True,
        client: Optional[httpx.Client] = None,
        multi_hop: bool = False,
        max_comments: int = 3,
    ) -> None:
        super().__init__(multi_hop=multi_hop, max_comments=max_comments)
        self._include_huxiu = include_huxiu
        self._api_key = os.getenv("SERPER_API_KEY", "") if include_serper else ""
        self._own_client = client is None
        self._client = client or httpx.Client(
            timeout=20.0,
            headers={"User-Agent": "IdeaHunter/0.1"},
        )

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> Kr36Scraper:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _fetch_rss(self, url: str, tag: str) -> list[RawItem]:
        try:
            r = self._client.get(url, timeout=12.0, follow_redirects=True)
            r.raise_for_status()
            entries = parse_feed(r.text)
        except Exception as exc:
            logger.warning("[%s] RSS 获取失败 %s: %s", tag, url, exc)
            return []

        items = []
        for e in entries:
            link = e.get("link", "")
            if not link:
                continue
            items.append(RawItem(
                id=f"{tag}_{abs(hash(link)) % 10**12}",
                url=link,
                title=e.get("title", ""),
                body=e.get("body", ""),
                source=self.name,
                extra={"via": "rss", "feed": tag},
                created_at=e.get("published_at") or datetime.now(timezone.utc),
            ))
        return items

    def _search_serper(self, query: str, num: int = 8) -> list[RawItem]:
        if not self._api_key:
            return []
        try:
            r = self._client.post(
                SERPER_URL,
                headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
                json={"q": query, "num": num},
                timeout=12.0,
            )
            r.raise_for_status()
            results = r.json().get("organic", [])
        except Exception as exc:
            logger.warning("36氪/虎嗅 Serper 失败: %s", exc)
            return []

        items = []
        for res in results:
            url = res.get("link", "")
            if not url:
                continue
            items.append(RawItem(
                id=f"kr36_{abs(hash(url)) % 10**12}",
                url=url,
                title=res.get("title", ""),
                body=res.get("snippet", ""),
                source=self.name,
                extra={"via": "search", "query": query},
                created_at=datetime.now(timezone.utc),
            ))
        return items

    def fetch_raw_items(
        self,
        *,
        max_items: Optional[int] = None,
        search_keywords: Optional[list[str]] = None,
    ) -> list[RawItem]:
        items: list[RawItem] = []

        # 36氪 RSS
        for i, (url, tag) in enumerate(KR36_FEEDS):
            if i:
                time.sleep(0.3)
            items.extend(self._fetch_rss(url, tag))

        # 虎嗅 RSS
        if self._include_huxiu:
            for url, tag in HUXIU_FEEDS:
                time.sleep(0.3)
                items.extend(self._fetch_rss(url, tag))

        # 关键词搜索
        if search_keywords and self._api_key:
            for i, kw in enumerate(search_keywords):
                if i:
                    time.sleep(0.5)
                items.extend(self._search_serper(
                    f'(site:36kr.com OR site:huxiu.com) {kw} (痛点 OR 问题 OR 创业)'
                ))

        seen: set[str] = set()
        unique = [it for it in items if not (it.id in seen or seen.add(it.id))]  # type: ignore
        if max_items:
            unique = unique[:max_items]

        logger.info("36氪+虎嗅采集: total_unique=%d", len(unique))
        return unique
