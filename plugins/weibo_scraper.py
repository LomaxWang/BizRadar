from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from plugins.base_scraper import BaseScraper, RawItem

logger = logging.getLogger(__name__)

# 微博移动端热搜 API（公开可用，无需登录）
WEIBO_HOT_API = "https://m.weibo.cn/api/container/getIndex"
WEIBO_HOT_CONTAINER = "106003type%3D25%26t%3D3%26disable_hot%3D1%26filter_type%3Drealtimehot"
SERPER_URL = "https://google.serper.dev/search"

# 过滤掉娱乐/体育词条的关键词（避免无关热搜）
NOISE_KEYWORDS = {"明星", "演员", "综艺", "歌手", "电影", "球队", "比赛", "冠军", "明星", "颁奖"}


class WeiboScraper(BaseScraper):
    """微博热搜 爬虫。

    工作流：
      1. 从微博移动端 API 拉取实时热搜 Top 50。
      2. 过滤娱乐/体育等无关词条，保留科技/商业/民生相关词条。
      3. 若配置了 SERPER_API_KEY，对每个热搜词在微博/知乎搜索讨论，
         寻找用户痛点（而非纯新闻报道）。

    环境变量：
        SERPER_API_KEY     - 可选，开启关联讨论搜索
        WEIBO_HOT_LIMIT    - 热搜词条数量上限，默认 20
        WEIBO_TECH_ONLY    - true = 只保留含技术/商业关键词的热搜（默认 true）
    """

    name = "weibo"

    def __init__(
        self,
        *,
        client: Optional[httpx.Client] = None,
        multi_hop: bool = False,
        max_comments: int = 3,
    ) -> None:
        super().__init__(multi_hop=multi_hop, max_comments=max_comments)
        self._api_key = os.getenv("SERPER_API_KEY", "")
        self._hot_limit = int(os.getenv("WEIBO_HOT_LIMIT", "20"))
        self._tech_only = os.getenv("WEIBO_TECH_ONLY", "true").lower() == "true"
        self._own_client = client is None
        self._client = client or httpx.Client(
            timeout=20.0,
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
                "Referer": "https://m.weibo.cn/",
            },
        )

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> WeiboScraper:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _fetch_hot_keywords(self) -> list[str]:
        """获取微博热搜关键词列表。"""
        try:
            r = self._client.get(
                WEIBO_HOT_API,
                params={"containerid": WEIBO_HOT_CONTAINER},
                timeout=12.0,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            logger.warning("微博热搜 API 获取失败: %s", exc)
            return []

        keywords: list[str] = []
        cards = data.get("data", {}).get("cards", [])
        for card in cards:
            for item in card.get("card_group", []):
                word = item.get("word") or item.get("desc", "")
                if word and len(word) >= 2:
                    keywords.append(word.strip())
                if len(keywords) >= self._hot_limit:
                    return keywords
        return keywords

    def _is_relevant(self, keyword: str) -> bool:
        """过滤纯娱乐/体育词条。"""
        if not self._tech_only:
            return True
        return not any(noise in keyword for noise in NOISE_KEYWORDS)

    def _search_discussions(self, keyword: str) -> list[RawItem]:
        """Serper 搜索该热搜词的微博/知乎痛点讨论。"""
        if not self._api_key:
            return []
        try:
            r = self._client.post(
                SERPER_URL,
                headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
                json={
                    "q": f'{keyword} (痛点 OR 建议 OR 投诉 OR 不满 OR 吐槽) site:weibo.com OR site:zhihu.com',
                    "num": 5,
                },
                timeout=12.0,
            )
            r.raise_for_status()
            results = r.json().get("organic", [])
        except Exception as exc:
            logger.debug("微博 Serper 搜索失败 %r: %s", keyword, exc)
            return []

        items = []
        for res in results:
            url = res.get("link", "")
            if not url:
                continue
            items.append(RawItem(
                id=f"weibo_{abs(hash(url)) % 10**12}",
                url=url,
                title=f"[热搜:{keyword}] {res.get('title', '')}",
                body=res.get("snippet", ""),
                source=self.name,
                extra={"hot_keyword": keyword, "via": "search"},
                created_at=datetime.now(timezone.utc),
            ))
        return items

    def fetch_raw_items(
        self,
        *,
        max_items: Optional[int] = None,
        search_keywords: Optional[list[str]] = None,
    ) -> list[RawItem]:
        hot_keywords = self._fetch_hot_keywords()
        relevant = [kw for kw in hot_keywords if self._is_relevant(kw)]
        logger.info("微博热搜: 共 %d 词条，过滤后保留 %d", len(hot_keywords), len(relevant))

        items: list[RawItem] = []

        # 为每个相关热搜词创建一条基础条目（热搜本身也是一个信号）
        for kw in relevant[:self._hot_limit]:
            items.append(RawItem(
                id=f"weibo_hot_{abs(hash(kw)) % 10**12}",
                url=f"https://s.weibo.com/weibo?q=%23{kw}%23",
                title=f"微博热搜: {kw}",
                body=f"微博实时热搜话题：{kw}。该话题当前在微博引发大量讨论，可能存在用户诉求或行业信号。",
                source=self.name,
                extra={"hot_keyword": kw, "via": "hot"},
                created_at=datetime.now(timezone.utc),
            ))

        # 若有 Serper Key，搜索相关讨论中的痛点
        if self._api_key:
            search_terms = relevant[:8]  # 限制 Serper 请求次数
            if search_keywords:
                search_terms = (search_keywords + search_terms)[:8]
            for i, kw in enumerate(search_terms):
                if i:
                    time.sleep(0.5)
                items.extend(self._search_discussions(kw))

        seen: set[str] = set()
        unique = [it for it in items if not (it.id in seen or seen.add(it.id))]  # type: ignore
        if max_items:
            unique = unique[:max_items]

        logger.info("微博采集: total_unique=%d", len(unique))
        return unique
