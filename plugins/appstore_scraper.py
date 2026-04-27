from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from plugins.base_scraper import BaseScraper, RawItem

logger = logging.getLogger(__name__)

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
# sortBy=mostCritical 已被苹果废弃，改为 mostRecent，过滤由代码处理
ITUNES_REVIEWS_URL = "https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"

# 美区默认英文搜索词；中国区请在 .env 中通过 APPSTORE_TERMS 覆盖
DEFAULT_TERMS_EN = [
    "project management", "invoicing", "time tracking",
    "expense report", "team collaboration", "crm",
    "customer support", "scheduling",
]
DEFAULT_TERMS_CN = [
    "项目管理", "记账", "工时统计", "客服", "排班", "销售管理",
]
DEFAULT_COUNTRY = "us"
CRITICAL_STARS = {1, 2}   # 只收集 1-2 星差评


class AppStoreScraper(BaseScraper):
    """App Store 差评爬虫（iTunes RSS API，无需任何 Key）。

    工作流：
      1. 通过 iTunes Search API 搜索目标品类，获取 App ID 列表。
      2. 对每个 App 请求 mostCritical 评论 RSS（JSON 格式）。
      3. 只保留 1-2 星评价，作为用户痛点原声。

    环境变量：
        APPSTORE_TERMS    - 逗号分隔的搜索词，默认内置 6 个品类
        APPSTORE_APP_IDS  - 直接指定 App ID（逗号分隔），跳过搜索步骤
        APPSTORE_COUNTRY  - 国家代码，默认 "us"（中国区用 "cn"）
    """

    name = "appstore"

    def __init__(
        self,
        *,
        terms: Optional[list[str]] = None,
        app_ids: Optional[list[str]] = None,
        country: Optional[str] = None,
        client: Optional[httpx.Client] = None,
        multi_hop: bool = False,
        max_comments: int = 3,
    ) -> None:
        super().__init__(multi_hop=multi_hop, max_comments=max_comments)
        self._country = country or os.getenv("APPSTORE_COUNTRY", DEFAULT_COUNTRY)
        raw_terms = os.getenv("APPSTORE_TERMS", "")
        default_terms = DEFAULT_TERMS_CN if self._country == "cn" else DEFAULT_TERMS_EN
        self._terms = terms or (
            [t.strip() for t in raw_terms.split(",") if t.strip()]
            if raw_terms else default_terms
        )
        raw_ids = os.getenv("APPSTORE_APP_IDS", "")
        self._fixed_app_ids = app_ids or (
            [i.strip() for i in raw_ids.split(",") if i.strip()]
            if raw_ids else []
        )
        self._own_client = client is None
        self._client = client or httpx.Client(
            timeout=20.0,
            headers={"User-Agent": "IdeaHunter/0.1"},
        )

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> AppStoreScraper:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _search_apps(self, term: str, limit: int = 5) -> list[str]:
        """通过 iTunes Search API 根据关键词获取 App ID 列表。"""
        try:
            r = self._client.get(
                ITUNES_SEARCH_URL,
                params={"term": term, "entity": "software", "limit": limit, "country": self._country},
                timeout=10.0,
            )
            r.raise_for_status()
            results = r.json().get("results", [])
            return [str(a["trackId"]) for a in results if "trackId" in a]
        except Exception as exc:
            logger.warning("App Store 搜索失败 term=%r: %s", term, exc)
            return []

    def _fetch_reviews(self, app_id: str) -> list[RawItem]:
        """获取指定 App 的差评列表（1-2星）。"""
        url = ITUNES_REVIEWS_URL.format(country=self._country, app_id=app_id)
        try:
            r = self._client.get(url, timeout=15.0)
            if r.status_code == 500:
                logger.warning("iTunes 评论 API 500，app_id=%s（苹果服务端问题，跳过）", app_id)
                return []
            r.raise_for_status()
            feed = r.json().get("feed", {})
            entries = feed.get("entry", [])
            # 第一条 entry 是 App 自身信息（iTunes 奇葩格式），需跳过
            if entries and "im:name" in entries[0]:
                entries = entries[1:]
        except Exception as exc:
            logger.debug("App Store 评论获取失败 app_id=%s: %s", app_id, exc)
            return []

        items = []
        for e in entries:
            try:
                rating = int(e.get("im:rating", {}).get("label", "5"))
            except (ValueError, TypeError):
                rating = 5
            if rating not in CRITICAL_STARS:
                continue

            title = e.get("title", {}).get("label", "")
            body = e.get("content", {}).get("label", "")
            app_name = e.get("im:voteCount", {}).get("label", app_id)  # fallback
            link = e.get("link", {}).get("attributes", {}).get("href", f"https://apps.apple.com/app/{app_id}")

            items.append(RawItem(
                id=f"appstore_{abs(hash(title + body)) % 10**12}",
                url=link,
                title=f"[{rating}★] {title}",
                body=body,
                source=self.name,
                extra={"app_id": app_id, "rating": rating},
                created_at=datetime.now(timezone.utc),
            ))
        return items

    def fetch_raw_items(
        self,
        *,
        max_items: Optional[int] = None,
        search_keywords: Optional[list[str]] = None,
    ) -> list[RawItem]:
        # 1. 收集 App ID：固定列表 + 搜索获取
        app_ids = list(self._fixed_app_ids)
        search_terms = (self._terms + (search_keywords or []))[:8]  # 限制请求次数
        for i, term in enumerate(search_terms):
            if i:
                time.sleep(0.3)
            app_ids.extend(self._search_apps(term, limit=3))

        # 去重 app_ids
        seen_ids: set[str] = set()
        unique_ids = [aid for aid in app_ids if not (aid in seen_ids or seen_ids.add(aid))]  # type: ignore
        unique_ids = unique_ids[:20]  # 最多抓 20 个 App 的评论

        # 2. 拉取差评
        items: list[RawItem] = []
        for i, app_id in enumerate(unique_ids):
            if i:
                time.sleep(0.4)
            reviews = self._fetch_reviews(app_id)
            items.extend(reviews)
            logger.debug("App %s: %d 条差评", app_id, len(reviews))

        # 去重 + 截断
        seen: set[str] = set()
        unique = [it for it in items if not (it.id in seen or seen.add(it.id))]  # type: ignore
        if max_items:
            unique = unique[:max_items]

        logger.info("App Store 差评采集: apps=%d, reviews=%d", len(unique_ids), len(unique))
        return unique
