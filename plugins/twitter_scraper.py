from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from plugins.base_scraper import BaseScraper, RawItem

logger = logging.getLogger(__name__)

TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
TWITTER_FIELDS = "created_at,author_id,public_metrics,entities"

# 高质量痛点搜索查询（Twitter 高级语法）
# 策略：用高置信度的痛点信号短语，而不是泛泛的 hashtag
DEFAULT_QUERIES = [
    # 英文：有明确工具需求的表达
    '("I wish there was" OR "why is there no tool" OR "does anyone know a tool") '
    '(workflow OR automation OR tracking OR report) -is:retweet lang:en min_faves:3',

    # 英文：#buildinpublic 社区的工具吐槽
    '#buildinpublic (problem OR "pain point" OR "spent hours" OR "manual process") '
    '-is:retweet lang:en min_faves:2',

    # 英文：独立开发者/创业者的日常抱怨
    '(#indiehackers OR #solofounder) ("still no good" OR "frustrating" OR "wish someone would build") '
    '-is:retweet lang:en',

    # 中文：工具和效率类痛点
    '("太麻烦了" OR "没有好用的" OR "求推荐工具" OR "每天手动") '
    '(效率 OR 工具 OR 自动化 OR 软件) -is:retweet lang:zh',

    # 中文：产品/职场吐槽
    '("为什么没有" OR "希望有个" OR "急需一个") '
    '(工具 OR 系统 OR 功能) -is:retweet lang:zh',
]


class TwitterScraper(BaseScraper):
    """Twitter/X 爬虫（需要 Twitter Developer 账号）。

    使用 Twitter API v2 recent search 端点。
    免费开发者账号支持约 50 万次 Tweet 读取/月，足够日常使用。

    环境变量：
        TWITTER_BEARER_TOKEN  - Twitter Developer 应用的 Bearer Token（必须）
        TWITTER_QUERIES       - 自定义搜索 Query（逗号分隔，可选）
        TWITTER_MAX_RESULTS   - 每个 Query 最多返回条数，默认 20，最大 100
    """

    name = "twitter"

    def __init__(
        self,
        *,
        bearer_token: Optional[str] = None,
        queries: Optional[list[str]] = None,
        client: Optional[httpx.Client] = None,
        multi_hop: bool = False,
        max_comments: int = 3,
    ) -> None:
        super().__init__(multi_hop=multi_hop, max_comments=max_comments)
        self._token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN", "")
        raw_queries = os.getenv("TWITTER_QUERIES", "")
        self._queries = queries or (
            [q.strip() for q in raw_queries.split("||") if q.strip()]
            if raw_queries else DEFAULT_QUERIES
        )
        self._max_results = int(os.getenv("TWITTER_MAX_RESULTS", "20"))
        self._own_client = client is None
        self._client = client or httpx.Client(
            timeout=20.0,
            headers={
                "Authorization": f"Bearer {self._token}",
                "User-Agent": "IdeaHunter/0.1",
            },
        )

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> TwitterScraper:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _search(self, query: str, max_results: int) -> list[RawItem]:
        try:
            r = self._client.get(
                TWITTER_SEARCH_URL,
                params={
                    "query": query,
                    "max_results": max(10, min(max_results, 100)),
                    "tweet.fields": TWITTER_FIELDS,
                    "expansions": "author_id",
                },
                timeout=15.0,
            )
            if r.status_code == 401:
                logger.error("Twitter: TWITTER_BEARER_TOKEN 无效或未配置")
                return []
            if r.status_code == 429:
                logger.warning("Twitter API 速率限制，等待 15 秒...")
                time.sleep(15)
                return []
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            logger.warning("Twitter 搜索失败 query=%r: %s", query[:40], exc)
            return []

        items = []
        for tweet in data.get("data", []):
            tweet_id = tweet.get("id", "")
            text = tweet.get("text", "")
            created = tweet.get("created_at", "")
            url = f"https://twitter.com/i/web/status/{tweet_id}"

            try:
                created_at = datetime.fromisoformat(created.replace("Z", "+00:00")) if created else None
            except Exception:
                created_at = None

            items.append(RawItem(
                id=f"tw_{tweet_id}",
                url=url,
                title=text[:80] + ("..." if len(text) > 80 else ""),
                body=text,
                source=self.name,
                extra={
                    "query": query[:60],
                    "likes": tweet.get("public_metrics", {}).get("like_count", 0),
                    "retweets": tweet.get("public_metrics", {}).get("retweet_count", 0),
                },
                created_at=created_at or datetime.now(timezone.utc),
            ))
        return items

    def fetch_raw_items(
        self,
        *,
        max_items: Optional[int] = None,
        search_keywords: Optional[list[str]] = None,
    ) -> list[RawItem]:
        if not self._token:
            logger.warning("Twitter: TWITTER_BEARER_TOKEN 未配置，跳过采集")
            return []

        items: list[RawItem] = []
        queries = list(self._queries)

        # 关键词追加到搜索
        if search_keywords:
            for kw in search_keywords[:3]:
                queries.append(f'{kw} (problem OR pain OR tool OR 问题 OR 工具) -is:retweet')

        for i, q in enumerate(queries):
            if i:
                time.sleep(1.5)  # Twitter API 速率限制友好请求
            results = self._search(q, self._max_results)
            items.extend(results)
            logger.debug("Twitter query %r: %d 条", q[:40], len(results))

        seen: set[str] = set()
        unique = [it for it in items if not (it.id in seen or seen.add(it.id))]  # type: ignore
        if max_items:
            unique = unique[:max_items]

        logger.info("Twitter 采集: total_unique=%d", len(unique))
        return unique
