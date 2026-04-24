from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from plugins.base_scraper import BaseScraper, RawItem
from plugins.feed_utils import parse_feed

logger = logging.getLogger(__name__)

SSPAI_RSS_URL = "https://sspai.com/feed"


class SspaiScraper(BaseScraper):
    """少数派（sspai.com）爬虫。

    通过公开 RSS 获取最新文章。少数派聚焦效率工具评测，
    评测文章中的「不足」「遗憾」「希望改进」等段落即为用户痛点。
    无需任何 API Key。
    """

    name = "sspai"

    def __init__(
        self,
        *,
        client: Optional[httpx.Client] = None,
        multi_hop: bool = False,
        max_comments: int = 3,
    ) -> None:
        super().__init__(multi_hop=multi_hop, max_comments=max_comments)
        self._own_client = client is None
        self._client = client or httpx.Client(
            timeout=20.0,
            headers={"User-Agent": "IdeaHunter/0.1"},
        )

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> SspaiScraper:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _fetch_page_body(self, url: str) -> str:
        """多跳：获取原文页面正文（少数派文章页公开可读）。"""
        import re
        try:
            r = self._client.get(url, timeout=10.0, follow_redirects=True)
            if r.status_code != 200:
                return ""
            paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", r.text, re.DOTALL)
            texts = [re.sub(r"<[^>]+>", "", p).strip() for p in paragraphs]
            return " ".join(t for t in texts if len(t) > 20)[:800]
        except Exception as exc:
            logger.debug("少数派原文获取失败 %s: %s", url, exc)
            return ""

    def fetch_raw_items(
        self,
        *,
        max_items: Optional[int] = None,
        search_keywords: Optional[list[str]] = None,
    ) -> list[RawItem]:
        try:
            r = self._client.get(SSPAI_RSS_URL, timeout=15.0)
            r.raise_for_status()
            entries = parse_feed(r.text)
        except Exception as exc:
            logger.warning("少数派 RSS 获取失败: %s", exc)
            return []

        limit = max_items or 30
        items: list[RawItem] = []
        for e in entries[:limit]:
            link = e.get("link", "")
            if not link:
                continue
            title = e.get("title", "")
            body = e.get("body", "")

            # 关键词过滤：优先保留评测/工具类文章
            if search_keywords:
                combined = (title + body).lower()
                if not any(kw.lower() in combined for kw in search_keywords):
                    continue

            items.append(RawItem(
                id=f"sspai_{abs(hash(link)) % 10**12}",
                url=link,
                title=title,
                body=body,
                source=self.name,
                extra={"via": "rss"},
                created_at=e.get("published_at") or datetime.now(timezone.utc),
            ))

        # 多跳：获取原文更多内容
        if self.multi_hop:
            for it in items:
                time.sleep(0.3)
                extra = self._fetch_page_body(it.url)
                if extra:
                    it.body = self._merge_comments(it.body, [extra])
                    logger.debug("少数派多跳: %s 追加正文", it.url)

        logger.info("少数派采集: %d 条", len(items))
        return items
