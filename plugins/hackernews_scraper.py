from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from plugins.base_scraper import BaseScraper, RawItem

HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"
DEFAULT_TAGS = ("ask_hn", "show_hn")


def _parse_iso_created(value: Any) -> Optional[datetime]:
    """Parse ISO-8601 timestamp from HN Algolia API (e.g. '2024-01-15T12:00:00.000Z')."""
    if not value:
        return None
    try:
        ts = str(value)
        # Handle trailing 'Z' for UTC
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None


class HackerNewsScraper(BaseScraper):
    """HackerNews scraper using the Algolia Search API."""

    name = "hackernews"

    def __init__(
        self,
        *,
        tags: Optional[tuple[str, ...]] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._tags = tags or DEFAULT_TAGS
        self._own_client = client is None
        self._client = client or httpx.Client(
            timeout=30.0,
            headers={"User-Agent": "IdeaHunter/0.1"},
        )

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> HackerNewsScraper:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _fetch_tag(self, tag: str, max_items: int) -> list[dict[str, Any]]:
        r = self._client.get(
            HN_ALGOLIA_URL,
            params={"tags": tag, "hitsPerPage": max_items},
        )
        r.raise_for_status()
        data = r.json()
        return data.get("hits", [])

    def fetch_raw_items(self, *, max_items: Optional[int] = None, search_keywords: Optional[list[str]] = None) -> list[RawItem]:
        per_tag = max_items or 25
        items: list[RawItem] = []

        for tag in self._tags:
            hits = self._fetch_tag(tag, per_tag)
            for h in hits:
                oid = h.get("objectID")
                if not oid:
                    continue
                body = h.get("story_text") or h.get("comment_text") or ""
                url = h.get("url") or f"https://news.ycombinator.com/item?id={oid}"
                items.append(
                    RawItem(
                        id=str(oid),
                        url=url,
                        title=str(h.get("title") or ""),
                        body=body,
                        source=self.name,
                        extra={"tag": tag, "author": h.get("author"), "points": h.get("points")},
                        created_at=_parse_iso_created(h.get("created_at")),
                    )
                )

        # Deduplicate by id
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
