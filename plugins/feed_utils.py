"""RSS 2.0 / Atom 1.0 通用解析工具，供各平台爬虫复用。"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional

_ATOM_NS = "http://www.w3.org/2005/Atom"
_CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"


def parse_feed(xml_text: str) -> list[dict]:
    """解析 RSS 2.0 / Atom 1.0，返回标准化条目列表。

    每条条目包含：title, link, body, published_at(datetime|None)
    """
    try:
        root = ET.fromstring(xml_text.strip())
    except ET.ParseError:
        return []

    entries: list[dict] = []

    # ── RSS 2.0 ──────────────────────────────────────────────────────────────
    for item in root.findall(".//item"):
        link = _text(item, "link") or _text(item, "guid")
        body = (
            _text(item, f"{{{_CONTENT_NS}}}encoded")
            or _text(item, "description")
        )
        entries.append({
            "title": _text(item, "title"),
            "link": link,
            "body": _strip_html(body),
            "published_at": _parse_rfc822(_text(item, "pubDate")),
        })

    # ── Atom 1.0 ─────────────────────────────────────────────────────────────
    for entry in root.iter(f"{{{_ATOM_NS}}}entry"):
        link_el = (
            entry.find(f"{{{_ATOM_NS}}}link[@rel='alternate']")
            or entry.find(f"{{{_ATOM_NS}}}link")
        )
        link = link_el.get("href", "") if link_el is not None else ""

        summary_el = entry.find(f"{{{_ATOM_NS}}}summary")
        content_el = entry.find(f"{{{_ATOM_NS}}}content")
        body = (
            (summary_el.text or "") if summary_el is not None else ""
        ) or (
            (content_el.text or "") if content_el is not None else ""
        )

        pub_el = entry.find(f"{{{_ATOM_NS}}}published") or entry.find(f"{{{_ATOM_NS}}}updated")
        title_el = entry.find(f"{{{_ATOM_NS}}}title")
        entries.append({
            "title": (title_el.text or "").strip() if title_el is not None else "",
            "link": link,
            "body": _strip_html(body),
            "published_at": _parse_iso((pub_el.text or "") if pub_el is not None else ""),
        })

    return entries


def _text(el: ET.Element, tag: str, default: str = "") -> str:
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else default


def _parse_rfc822(s: str) -> Optional[datetime]:
    try:
        return parsedate_to_datetime(s) if s else None
    except Exception:
        return None


def _parse_iso(s: str) -> Optional[datetime]:
    try:
        s = s.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s) if s else None
    except Exception:
        return None


def _strip_html(text: str) -> str:
    """简单去除 HTML 标签，保留纯文本。"""
    import re
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text
