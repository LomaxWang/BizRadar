from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from plugins.base_scraper import BaseScraper

# Registry dict mapping name -> scraper class
SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {}


def register_scraper(name: str, cls: type[BaseScraper]) -> None:
    """Register a scraper class under the given name."""
    SCRAPER_REGISTRY[name] = cls


def get_scraper(name: str) -> BaseScraper:
    """Instantiate and return a scraper by name. Raises ValueError for unknown names."""
    key = name.strip().lower()
    if key not in SCRAPER_REGISTRY:
        raise ValueError(f"Unknown source: {name!r}. Available: {sorted(SCRAPER_REGISTRY)}")
    return SCRAPER_REGISTRY[key]()
