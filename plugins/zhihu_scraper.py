"""知乎 (Zhihu) scraper — 通过 Google Serper 搜索知乎问答.

与 xhs_scraper 相同策略：使用 Serper.dev 搜索
  site:zhihu.com 的痛点/求推荐帖，无需知乎账号或 Cookie。

环境变量：
    SERPER_API_KEY   - Serper.dev 的 API Key（必须）
    ZHIHU_QUERIES    - 自定义搜索词（逗号分隔，可选）
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from plugins.base_scraper import BaseScraper, RawItem

logger = logging.getLogger(__name__)

SERPER_API_URL = "https://google.serper.dev/search"

_DEFAULT_QUERIES = [
    "site:zhihu.com 有什么好用的工具 推荐",
    "site:zhihu.com 每天都要手动 很烦",
    "site:zhihu.com 求推荐 工具 效率",
    "site:zhihu.com 有没有什么软件 可以自动",
    "site:zhihu.com 痛点 中小企业 SaaS 工具",
]
_DEFAULT_MAX_RESULTS = 10


class ZhihuScraper(BaseScraper):
    """知乎商业痛点爬虫（Google Serper 搜索实现）。

    多跳模式（multi_hop=True）：
        搜到结果后尝试 GET 知乎原页，提取回答正文补充 snippet。
        知乎部分页面公开可读，部分需登录（静默 fallback）。
    """

    name = "zhihu"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        queries: Optional[list[str]] = None,
        client: Optional[httpx.Client] = None,
        multi_hop: bool = False,
        max_comments: int = 3,
    ) -> None:
        super().__init__(multi_hop=multi_hop, max_comments=max_comments)
        self._api_key = api_key or os.getenv("SERPER_API_KEY", "")
        raw_queries = os.getenv("ZHIHU_QUERIES", "")
        self._queries = queries or (
            [q.strip() for q in raw_queries.split(",") if q.strip()]
            if raw_queries
            else _DEFAULT_QUERIES
        )
        self._own_client = client is None
        self._client = client or httpx.Client(timeout=30.0, headers={"User-Agent": "IdeaHunter/0.1"})

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def _fetch_page_text(self, url: str) -> str:
        """第二跳：尝试获取知乎原页正文段落。"""
        import re
        try:
            r = self._client.get(url, timeout=8.0, follow_redirects=True)
            if r.status_code != 200:
                return ""
            html = r.text
            paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL)
            texts = [re.sub(r"<[^>]+>", "", p).strip() for p in paragraphs]
            result = " ".join(t for t in texts if len(t) > 15)
            return result[:600]
        except Exception as exc:
            logger.debug("知乎页面获取失败 %s: %s", url, exc)
            return ""

    def _search_serper(self, query: str, num: int = _DEFAULT_MAX_RESULTS) -> list[dict[str, Any]]:
        if not self._api_key:
            logger.warning("ZhihuScraper: SERPER_API_KEY 未配置，跳过查询: %s", query)
            return []
        resp = self._client.post(
            SERPER_API_URL,
            headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
            json={"q": query, "num": num, "gl": "cn", "hl": "zh-cn"},
        )
        resp.raise_for_status()
        return resp.json().get("organic", [])

    def fetch_raw_items(self, *, max_items: Optional[int] = None, search_keywords: Optional[list[str]] = None) -> list[RawItem]:
        if not self._api_key:
            logger.error(
                "ZhihuScraper: SERPER_API_KEY 未设置，无法抓取知乎数据。"
                "请在 .env 中配置 SERPER_API_KEY=<your_key>"
            )
            return []

        seen: set[str] = set()
        items: list[RawItem] = []
        per_query = max_items // len(self._queries) + 1 if max_items else _DEFAULT_MAX_RESULTS

        for i, query in enumerate(self._queries):
            if max_items and len(items) >= max_items:
                break
            if i:
                time.sleep(0.5)
            try:
                results = self._search_serper(query, num=min(per_query, _DEFAULT_MAX_RESULTS))
            except Exception as exc:
                logger.warning("ZhihuScraper: 查询 %r 失败: %s", query, exc)
                continue

            for result in results:
                url: str = result.get("link", "")
                if not url or url in seen:
                    continue
                seen.add(url)

                title = result.get("title", "").strip()
                # 知乎标题末尾常带" - 知乎"，去掉
                title = title.removesuffix(" - 知乎")
                snippet = result.get("snippet", "").strip()
                if "·" in snippet:
                    snippet = snippet.split("·", 1)[-1].strip()

                items.append(
                    RawItem(
                        id=f"zhihu_{abs(hash(url)) % (10 ** 12)}",
                        url=url,
                        title=title,
                        body=snippet,
                        source=self.name,
                        extra={"query": query},
                        created_at=datetime.now(timezone.utc),
                    )
                )
                if max_items and len(items) >= max_items:
                    break

        # 多跳：尝试获取知乎原页正文
        if self.multi_hop:
            for it in items:
                time.sleep(0.3)
                extra_text = self._fetch_page_text(it.url)
                if extra_text:
                    it.body = it.body + "\n\n" + extra_text
                    logger.debug("知乎多跳: %s 追加 %d 字", it.url, len(extra_text))

        return items
