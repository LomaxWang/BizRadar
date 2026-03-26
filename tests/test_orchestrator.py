"""Tests for pure helper functions in core.orchestrator."""

from __future__ import annotations

import pytest

from core.orchestrator import (
    _build_ingest_item,
    _compact_dict,
    _keyword_match,
    _normalize_ingest_text,
    _slug,
)
from plugins.base_scraper import RawItem


# ---------- _slug ----------


class TestSlug:
    def test_simple_ascii(self):
        assert _slug("Hello World") == "hello-world"

    def test_special_characters_replaced(self):
        result = _slug("foo@bar#baz!!")
        assert result == "foo-bar-baz"

    def test_multiple_dashes_collapsed(self):
        result = _slug("foo---bar")
        assert result == "foo-bar"

    def test_leading_trailing_dashes_stripped(self):
        result = _slug("--hello--")
        assert result == "hello"

    def test_max_len_truncation(self):
        long = "a" * 100
        result = _slug(long, max_len=10)
        assert len(result) <= 10

    def test_empty_string_returns_idea(self):
        assert _slug("") == "idea"

    def test_chinese_characters_preserved(self):
        result = _slug("你好世界 test")
        assert "你好世界" in result

    def test_whitespace_only_returns_idea(self):
        assert _slug("   ") == "idea"


# ---------- _keyword_match ----------


class TestKeywordMatch:
    def _item(self, title: str = "", body: str = "") -> RawItem:
        return RawItem(id="1", title=title, body=body, source="test")

    def test_no_keywords_always_matches(self):
        assert _keyword_match(self._item(title="anything"), None) is True
        assert _keyword_match(self._item(title="anything"), []) is True

    def test_keyword_in_title(self):
        item = self._item(title="Python is great", body="")
        assert _keyword_match(item, ["python"]) is True

    def test_keyword_in_body(self):
        item = self._item(title="", body="I love FastAPI")
        assert _keyword_match(item, ["fastapi"]) is True

    def test_no_keyword_match(self):
        item = self._item(title="Hello", body="World")
        assert _keyword_match(item, ["python"]) is False

    def test_case_insensitive(self):
        item = self._item(title="PYTHON is great")
        assert _keyword_match(item, ["python"]) is True

    def test_any_keyword_matches(self):
        item = self._item(title="FastAPI web", body="")
        assert _keyword_match(item, ["django", "fastapi"]) is True


# ---------- _compact_dict ----------


class TestCompactDict:
    def test_removes_none(self):
        assert _compact_dict({"a": 1, "b": None}) == {"a": 1}

    def test_removes_empty_string(self):
        assert _compact_dict({"a": "hello", "b": ""}) == {"a": "hello"}

    def test_removes_whitespace_only_string(self):
        assert _compact_dict({"a": "ok", "b": "   "}) == {"a": "ok"}

    def test_removes_empty_list(self):
        assert _compact_dict({"a": [1], "b": []}) == {"a": [1]}

    def test_removes_empty_dict(self):
        assert _compact_dict({"a": {"k": "v"}, "b": {}}) == {"a": {"k": "v"}}

    def test_preserves_zero(self):
        assert _compact_dict({"a": 0}) == {"a": 0}

    def test_preserves_false(self):
        assert _compact_dict({"a": False}) == {"a": False}

    def test_all_empty(self):
        assert _compact_dict({"a": None, "b": "", "c": [], "d": {}}) == {}


# ---------- _normalize_ingest_text ----------


class TestNormalizeIngestText:
    def test_collapses_whitespace(self):
        assert _normalize_ingest_text("hello   world") == "hello world"

    def test_strips_edges(self):
        assert _normalize_ingest_text("  hello  ") == "hello"

    def test_newlines_and_tabs(self):
        assert _normalize_ingest_text("a\n\n\tb") == "a b"

    def test_empty_string(self):
        assert _normalize_ingest_text("") == ""


# ---------- _build_ingest_item ----------


class TestBuildIngestItem:
    def test_returns_raw_item(self):
        item = _build_ingest_item("webhook", 0, "some complaint text")
        assert item.source == "webhook"
        assert item.id.startswith("ingest_")
        assert "外部注入-1" in item.title
        assert item.body == "some complaint text"

    def test_deterministic_id(self):
        """Same source + normalized text -> same id."""
        item1 = _build_ingest_item("src", 0, "hello  world")
        item2 = _build_ingest_item("src", 0, "hello  world")
        assert item1.id == item2.id

    def test_different_text_different_id(self):
        item1 = _build_ingest_item("src", 0, "text one")
        item2 = _build_ingest_item("src", 0, "text two")
        assert item1.id != item2.id

    def test_index_in_title(self):
        item = _build_ingest_item("src", 5, "hello")
        assert "外部注入-6" in item.title  # idx+1
