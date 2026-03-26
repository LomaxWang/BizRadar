from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from plugins.base_scraper import BaseScraper, RawItem

V2EX_TOPICS_URL = "https://www.v2ex.com/api/topics/show.json"
DEFAULT_NODES = ("qna", "create")
REQUEST_DELAY_SEC = 0.35


def _parse_created(ts: Any) -> Optional[datetime]:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


class V2EXScraper(BaseScraper):
    """V2EX 节点最新主题（官方 JSON API）。"""

    name = "v2ex"

    def __init__(
        self,
        *,
        nodes: Optional[tuple[str, ...]] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._nodes = nodes or DEFAULT_NODES
        self._own_client = client is None
        self._client = client or httpx.Client(timeout=30.0, headers={"User-Agent": "IdeaHunter/0.1"})

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> V2EXScraper:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _fetch_node(self, node_name: str) -> list[dict[str, Any]]:
        r = self._client.get(V2EX_TOPICS_URL, params={"node_name": node_name})
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            return []
        return data

    def fetch_raw_items(self, *, max_items: Optional[int] = None) -> list[RawItem]:
        items: list[RawItem] = []
        for i, node in enumerate(self._nodes):
            if i:
                time.sleep(REQUEST_DELAY_SEC)
            topics = self._fetch_node(node)
            for t in topics:
                tid = t.get("id")
                if tid is None:
                    continue
                topic_id = str(tid)
                url = str(t.get("url") or f"https://www.v2ex.com/t/{topic_id}")
                title = str(t.get("title") or "")
                content = str(t.get("content") or "")
                items.append(
                    RawItem(
                        id=topic_id,
                        url=url,
                        title=title,
                        body=content,
                        source=self.name,
                        extra={"node": node, "member": t.get("member")},
                        created_at=_parse_created(t.get("created")),
                    )
                )

        # 去重同一 topic（多节点一般不会重复，保险起见按 id）
        seen: set[str] = set()
        unique: list[RawItem] = []
        for it in items:
            if it.id in seen:
                continue
            seen.add(it.id)
            unique.append(it)

        if max_items is not None:
            unique = unique[: max(0, max_items)]
        return unique
