from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from plugins.base_scraper import BaseScraper, RawItem
from plugins.feed_utils import parse_feed

logger = logging.getLogger(__name__)

IH_RSS_URL = "https://www.indiehackers.com/feed.xml"
SERPER_URL = "https://google.serper.dev/search"
DEFAULT_IH_QUERIES = [
    'site:indiehackers.com "what tool" OR "does anyone else" OR "wish there was"',
    'site:indiehackers.com "biggest problem" OR "pain point" OR "struggle with"',
]


class IndieHackersScraper(BaseScraper):
    """IndieHackers 爬虫。

    New 轨：Atom RSS Feed，抓取创业者最新文章与讨论。
    Search 轨：Serper 搜索 IH 论坛痛点讨论帖。
    多跳：暂不支持（IH 页面需登录加载完整评论）。
    """

    name = "indiehackers"

    def __init__(
        self,
        *,
        serper_api_key: Optional[str] = None,
        client: Optional[httpx.Client] = None,
        multi_hop: bool = False,
        max_comments: int = 3,
    ) -> None:
        super().__init__(multi_hop=multi_hop, max_comments=max_comments)
        self._api_key = serper_api_key or os.getenv("SERPER_API_KEY", "")
        self._own_client = client is None
        self._client = client or httpx.Client(
            timeout=20.0,
            headers={"User-Agent": "IdeaHunter/0.1"},
        )

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> IndieHackersScraper:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _fetch_rss(self, limit: int) -> list[RawItem]:
        try:
            r = self._client.get(IH_RSS_URL, timeout=15.0)
            r.raise_for_status()
            entries = parse_feed(r.text)
        except Exception as exc:
            logger.warning("IndieHackers RSS 获取失败: %s", exc)
            return []

        items = []
        for e in entries[:limit]:
            link = e.get("link", "")
            if not link:
                continue
            items.append(RawItem(
                id=f"ih_{abs(hash(link)) % 10**12}",
                url=link,
                title=e.get("title", ""),
                body=e.get("body", ""),
                source=self.name,
                extra={"via": "rss"},
                created_at=e.get("published_at") or datetime.now(timezone.utc),
            ))
        return items

    def _search_serper(self, query: str, num: int = 10) -> list[RawItem]:
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
            logger.warning("IndieHackers Serper 失败: %s", exc)
            return []

        items = []
        for res in results:
            url = res.get("link", "")
            if not url:
                continue
            items.append(RawItem(
                id=f"ih_{abs(hash(url)) % 10**12}",
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
        limit = max_items or 30
        items: list[RawItem] = []

        items.extend(self._fetch_rss(limit))

        queries = DEFAULT_IH_QUERIES.copy()
        if search_keywords:
            queries += [f'site:indiehackers.com {kw}' for kw in search_keywords]

        for i, q in enumerate(queries):
            if i:
                time.sleep(0.5)
            items.extend(self._search_serper(q, num=8))

        seen: set[str] = set()
        unique = [it for it in items if not (it.id in seen or seen.add(it.id))]  # type: ignore
        if max_items:
            unique = unique[:max_items]

        logger.info("IndieHackers 采集: total_unique=%d", len(unique))
        return unique
