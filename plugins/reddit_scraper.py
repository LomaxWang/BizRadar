from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from plugins.base_scraper import BaseScraper, RawItem

REDDIT_BASE_URL = "https://www.reddit.com/r/{subreddit}/new.json"
DEFAULT_SUBREDDITS = ("SaaS", "Entrepreneur", "SideProject")
USER_AGENT = "IdeaHunter/0.1 (business radar)"


def _parse_utc_timestamp(ts: Any) -> Optional[datetime]:
    """Parse a Unix UTC timestamp (float) from Reddit API."""
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


class RedditScraper(BaseScraper):
    """Reddit scraper using the public JSON API."""

    name = "reddit"

    def __init__(
        self,
        *,
        subreddits: Optional[tuple[str, ...]] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._subreddits = subreddits or DEFAULT_SUBREDDITS
        self._own_client = client is None
        self._client = client or httpx.Client(
            timeout=30.0,
            headers={"User-Agent": USER_AGENT},
        )

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self) -> RedditScraper:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _fetch_subreddit(self, subreddit: str, limit: int) -> list[dict[str, Any]]:
        url = REDDIT_BASE_URL.format(subreddit=subreddit)
        r = self._client.get(url, params={"limit": limit})
        r.raise_for_status()
        data = r.json()
        children = data.get("data", {}).get("children", [])
        return [c.get("data", {}) for c in children if c.get("data")]

    def fetch_raw_items(self, *, max_items: Optional[int] = None) -> list[RawItem]:
        per_sub = max_items or 25
        items: list[RawItem] = []

        for subreddit in self._subreddits:
            posts = self._fetch_subreddit(subreddit, per_sub)
            for p in posts:
                post_id = p.get("id")
                if not post_id:
                    continue
                permalink = p.get("permalink", "")
                url = f"https://www.reddit.com{permalink}" if permalink else ""
                items.append(
                    RawItem(
                        id=str(post_id),
                        url=url,
                        title=str(p.get("title") or ""),
                        body=str(p.get("selftext") or ""),
                        source=self.name,
                        extra={
                            "subreddit": subreddit,
                            "author": p.get("author"),
                            "score": p.get("score"),
                        },
                        created_at=_parse_utc_timestamp(p.get("created_utc")),
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
