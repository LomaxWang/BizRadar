"""小红书 (Xiaohongshu) scraper via search API.

由于小红书无官方公开 API，本实现通过以下两种可选方式工作：

方式 A（推荐/默认）：使用 Serper.dev Google Search API 搜索
  小红书投诉/痛点帖子（需在 .env 中配置 SERPER_API_KEY）。

方式 B（回退）：直接抓取 xiaohongshu.com 的搜索结果页（需要
  headers + cookie，实际部署时仍有反爬风险）。

本版本使用方式 A ——代价最小、最稳定，不需要登录态。
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

# 只保留主站用户内容页，排除招聘/广告/備案等子站
_BLOCKED_HOSTS = {
    "job.xiaohongshu.com",
    "ad.xiaohongshu.com",
    "fuwu.xiaohongshu.com",
    "rpdc.xiaohongshu.com",
    "beian.xiaohongshu.com",
    "developer.xiaohongshu.com",
    "business.xiaohongshu.com",
}

# 搜索词聚焦吸槽/投诉/痛点语气，而非推荐攻略
_DEFAULT_QUERIES = [
    'site:www.xiaohongshu.com "太烦了" "每次都要"',
    'site:www.xiaohongshu.com "好麻烦" "手动" "没有工具"',
    'site:www.xiaohongshu.com "能不能" "自动" "浏览器" OR "应用"',
    'site:www.xiaohongshu.com "吃了大乏头" OR "设计缺陷" OR "体验很差"',
    'site:www.xiaohongshu.com "没有好用的" "软件" "卡麻了"',
]
_DEFAULT_MAX_RESULTS = 10  # per query


class XhsScraper(BaseScraper):
    """小红书商业痛点爬虫（Google Serper 搜索实现）。

    多跳模式（multi_hop=True）：
        搜到结果后尝试 GET 原页面，提取 <p> 文本补充 snippet。
        小红书需登录，通常会返回登录页，此时静默 fallback 到原 snippet。

    环境变量：
        SERPER_API_KEY  - Serper.dev 的 API Key（必须）
        XHS_QUERIES     - 自定义搜索词列表（逗号分隔，可选）
    """

    name = "xhs"

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
        raw_queries = os.getenv("XHS_QUERIES", "")
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

    def _search_serper(self, query: str, num: int = _DEFAULT_MAX_RESULTS) -> list[dict[str, Any]]:
        """调用 Serper.dev API 获取搜索结果。"""
        if not self._api_key:
            logger.warning("XhsScraper: SERPER_API_KEY 未配置，跳过查询: %s", query)
            return []
        resp = self._client.post(
            SERPER_API_URL,
            headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
            json={"q": query, "num": num, "gl": "cn", "hl": "zh-cn"},
        )
        resp.raise_for_status()
        return resp.json().get("organic", [])

    def _is_content_url(self, url: str) -> bool:
        """URL 过滤：只保留主站用户内容页。"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            # 拒绝已知非内容子域名
            if host in _BLOCKED_HOSTS:
                return False
            # 只要 xiaohongshu.com 主域即可
            if "xiaohongshu.com" not in host:
                return False
            # 过滤首页根路径（无实质内容）
            path = parsed.path.rstrip("/")
            if not path:
                return False
            return True
        except Exception:
            return True

    def _fetch_page_text(self, url: str) -> str:
        """第二跳：尝试获取原页面文本（需登录的页面会 fallback）。"""
        import re
        try:
            r = self._client.get(url, timeout=8.0, follow_redirects=True)
            if r.status_code != 200:
                return ""
            html = r.text
            # 简单提取 <p> 标签内容，去掉 HTML 标签
            paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL)
            texts = [re.sub(r"<[^>]+>", "", p).strip() for p in paragraphs]
            result = " ".join(t for t in texts if len(t) > 10)
            return result[:500]  # 最多追加 500 字
        except Exception as exc:
            logger.debug("XHS 页面获取失败 %s: %s", url, exc)
            return ""

    def fetch_raw_items(self, *, max_items: Optional[int] = None, search_keywords: Optional[list[str]] = None) -> list[RawItem]:
        if not self._api_key:
            logger.error(
                "XhsScraper: SERPER_API_KEY 未设置，无法抓取小红书数据。"
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
                logger.warning("XhsScraper: 查询 %r 失败: %s", query, exc)
                continue

            for result in results:
                url: str = result.get("link", "")
                if not url or url in seen:
                    continue
                # 过滤非内容子域名（招聘、广告、备案等）
                if not self._is_content_url(url):
                    logger.debug("XhsScraper: 跳过非内容URL: %s", url)
                    continue
                seen.add(url)

                title = result.get("title", "").strip()
                snippet = result.get("snippet", "").strip()
                # 简单去掉日期前缀（如 "2024年1月1日 · "）
                if "·" in snippet:
                    snippet = snippet.split("·", 1)[-1].strip()

                items.append(
                    RawItem(
                        id=f"xhs_{abs(hash(url)) % (10 ** 12)}",
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

        # 多跳：尝试获取原页面正文（小红书需登录，大概率 fallback）
        if self.multi_hop:
            for it in items:
                time.sleep(0.3)
                extra_text = self._fetch_page_text(it.url)
                if extra_text:
                    it.body = it.body + "\n\n" + extra_text
                    logger.debug("XHS 多跳: %s 追加 %d 字", it.url, len(extra_text))

        return items
