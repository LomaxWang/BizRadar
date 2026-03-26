"""Tests for plugins.v2ex_scraper.V2EXScraper using respx to mock httpx."""

from __future__ import annotations

import httpx
import pytest
import respx

from plugins.v2ex_scraper import V2EX_TOPICS_URL, V2EXScraper


def _make_topic(tid: int, *, node: str = "qna", title: str = "") -> dict:
    return {
        "id": tid,
        "title": title or f"Topic {tid}",
        "content": f"Body of topic {tid}",
        "url": f"https://www.v2ex.com/t/{tid}",
        "created": 1700000000 + tid,
        "member": {"username": f"user{tid}"},
    }


@respx.mock
class TestV2EXScraperNormal:
    def test_single_node_fetch(self):
        topics = [_make_topic(1), _make_topic(2)]
        respx.get(V2EX_TOPICS_URL, params={"node_name": "qna"}).respond(
            200, json=topics
        )

        scraper = V2EXScraper(nodes=("qna",), client=httpx.Client())
        items = scraper.fetch_raw_items()

        assert len(items) == 2
        assert items[0].id == "1"
        assert items[0].title == "Topic 1"
        assert items[0].source == "v2ex"
        assert items[1].id == "2"

    def test_multiple_nodes(self):
        respx.get(V2EX_TOPICS_URL, params={"node_name": "qna"}).respond(
            200, json=[_make_topic(1)]
        )
        respx.get(V2EX_TOPICS_URL, params={"node_name": "create"}).respond(
            200, json=[_make_topic(2)]
        )

        scraper = V2EXScraper(nodes=("qna", "create"), client=httpx.Client())
        items = scraper.fetch_raw_items()

        assert len(items) == 2
        ids = {it.id for it in items}
        assert ids == {"1", "2"}


@respx.mock
class TestV2EXScraperEmpty:
    def test_empty_response(self):
        respx.get(V2EX_TOPICS_URL, params={"node_name": "qna"}).respond(
            200, json=[]
        )
        scraper = V2EXScraper(nodes=("qna",), client=httpx.Client())
        items = scraper.fetch_raw_items()
        assert items == []

    def test_non_list_response_treated_as_empty(self):
        respx.get(V2EX_TOPICS_URL, params={"node_name": "qna"}).respond(
            200, json={"error": "rate limited"}
        )
        scraper = V2EXScraper(nodes=("qna",), client=httpx.Client())
        items = scraper.fetch_raw_items()
        assert items == []


@respx.mock
class TestV2EXScraperDedup:
    def test_duplicate_ids_removed(self):
        topic = _make_topic(42)
        # Same topic appears in both nodes
        respx.get(V2EX_TOPICS_URL, params={"node_name": "qna"}).respond(
            200, json=[topic]
        )
        respx.get(V2EX_TOPICS_URL, params={"node_name": "create"}).respond(
            200, json=[topic]
        )

        scraper = V2EXScraper(nodes=("qna", "create"), client=httpx.Client())
        items = scraper.fetch_raw_items()

        assert len(items) == 1
        assert items[0].id == "42"


@respx.mock
class TestV2EXScraperMaxItems:
    def test_max_items_truncation(self):
        topics = [_make_topic(i) for i in range(10)]
        respx.get(V2EX_TOPICS_URL, params={"node_name": "qna"}).respond(
            200, json=topics
        )

        scraper = V2EXScraper(nodes=("qna",), client=httpx.Client())
        items = scraper.fetch_raw_items(max_items=3)

        assert len(items) == 3

    def test_max_items_zero(self):
        topics = [_make_topic(i) for i in range(5)]
        respx.get(V2EX_TOPICS_URL, params={"node_name": "qna"}).respond(
            200, json=topics
        )

        scraper = V2EXScraper(nodes=("qna",), client=httpx.Client())
        items = scraper.fetch_raw_items(max_items=0)

        assert len(items) == 0

    def test_max_items_none_returns_all(self):
        topics = [_make_topic(i) for i in range(5)]
        respx.get(V2EX_TOPICS_URL, params={"node_name": "qna"}).respond(
            200, json=topics
        )

        scraper = V2EXScraper(nodes=("qna",), client=httpx.Client())
        items = scraper.fetch_raw_items(max_items=None)

        assert len(items) == 5
