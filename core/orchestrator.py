from __future__ import annotations

import hashlib
import logging
import re
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import Settings, get_settings
from core.agents import run_critic, run_extractor, run_planner, run_pm
from core.memory.sqlite_manager import SqliteManager
from plugins.base_scraper import BaseScraper, RawItem
from plugins.registry import get_scraper

logger = logging.getLogger(__name__)

SCORE_APPROVE_MIN = 80
MIN_TEXT_CHARS = 12


def _slug(s: str, max_len: int = 48) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", s.strip().lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return (s[:max_len] or "idea").rstrip("-")


def _keyword_match(item: RawItem, keywords: Optional[list[str]]) -> bool:
    if not keywords:
        return True
    blob = f"{item.title}\n{item.body}".lower()
    return any(k.lower() in blob for k in keywords)


def _compact_dict(data: dict[str, object]) -> dict[str, object]:
    compacted: dict[str, object] = {}
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        compacted[key] = value
    return compacted


def _mark_processed(
    db: SqliteManager,
    item: RawItem,
    outcome: str,
    *,
    details: Optional[dict[str, object]] = None,
) -> None:
    db.mark_processed(
        item.source,
        item.id,
        outcome,
        title=item.title,
        url=item.url,
        details=_compact_dict(details or {}),
    )


def _normalize_ingest_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _build_ingest_item(source_name: str, idx: int, text: str) -> RawItem:
    normalized = _normalize_ingest_text(text)
    digest = hashlib.sha256(f"{source_name}\n{normalized}".encode("utf-8")).hexdigest()[:16]
    preview = normalized[:24]
    title = f"外部注入-{idx + 1}"
    if preview:
        title = f"外部注入-{idx + 1}: {preview}"
    return RawItem(
        id=f"ingest_{digest}",
        url="",
        title=title,
        body=text,
        source=source_name,
        extra={"ingest_hash": digest},
    )


@dataclass
class RunStats:
    fetched: int = 0
    skipped_duplicate: int = 0
    skipped_keywords: int = 0
    skipped_short: int = 0
    dropped: int = 0
    rejected: int = 0
    approved: int = 0
    errors: int = 0
    ideas: list[dict] = field(default_factory=list)


OnProgress = Callable[[str], None]


def _process_items(
    items: list[RawItem],
    *,
    settings: Settings,
    db: SqliteManager,
    output_dir: str | Path,
    keywords: Optional[list[str]] = None,
    on_progress: Optional[OnProgress] = None,
    progress_prefix: str = "分析",
) -> RunStats:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stats = RunStats(fetched=len(items))

    def prog(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    for idx, item in enumerate(items):
        text_len = len(item.title) + len(item.body)
        base_details: dict[str, object] = {
            "text_length": text_len,
            "source": item.source,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }

        if db.is_processed(item.source, item.id):
            stats.skipped_duplicate += 1
            continue
        if not _keyword_match(item, keywords):
            stats.skipped_keywords += 1
            _mark_processed(
                db,
                item,
                "skipped_keywords",
                details={**base_details, "keywords": keywords or []},
            )
            continue
        if text_len < MIN_TEXT_CHARS:
            stats.skipped_short += 1
            _mark_processed(db, item, "skipped_short", details=base_details)
            continue

        prog(f"{progress_prefix} {idx + 1}/{len(items)}: {item.title[:60]}…")

        trace_details = dict(base_details)
        try:
            ex = run_extractor(settings, item)
            trace_details.update(
                {
                    "extractor_has_pain_point": ex.has_pain_point,
                    "extractor_summary": ex.summary,
                    "extracted_complaint": ex.extracted_complaint,
                }
            )
            if not ex.has_pain_point:
                stats.dropped += 1
                _mark_processed(db, item, "dropped", details=trace_details)
                continue

            pm = run_pm(
                settings,
                title=item.title,
                url=item.url,
                extracted_complaint=ex.extracted_complaint or ex.summary,
                summary=ex.summary,
            )
            trace_details.update(
                {
                    "user_story": pm.user_story,
                    "persona": pm.persona,
                }
            )

            cr = run_critic(
                settings,
                user_story=pm.user_story,
                persona=pm.persona,
                title=item.title,
                url=item.url,
            )
            trace_details.update(
                {
                    "critic_score": cr.score,
                    "critic_reasoning": cr.reasoning,
                    "competitors_note": cr.competitors_note,
                }
            )

            if cr.score < SCORE_APPROVE_MIN:
                stats.rejected += 1
                _mark_processed(db, item, "rejected", details=trace_details)
                continue

            pl = run_planner(
                settings,
                user_story=pm.user_story,
                persona=pm.persona,
                critic_reasoning=cr.reasoning,
                competitors_note=cr.competitors_note,
                score=cr.score,
                title=item.title,
                url=item.url,
                source=item.source,
            )
            trace_details.update(
                {
                    "planner_title": pl.title,
                    "target_audience": pl.target_audience,
                    "tech_stack": pl.tech_stack,
                }
            )

            idea_title = pl.title or item.title
            idea_id = db.insert_idea(
                title=idea_title,
                score=cr.score,
                source=item.source,
                markdown_prd=pl.markdown_prd,
                tech_stack=pl.tech_stack or ["待定"],
                target_audience=pl.target_audience or pm.persona,
                raw_complaints_analyzed=1,
                external_ref=item.id,
            )
            fname = f"{idea_id}_{_slug(idea_title)}.md"
            fpath = out / fname
            fpath.write_text(pl.markdown_prd, encoding="utf-8")

            stats.approved += 1
            trace_details.update({"idea_id": idea_id, "output_path": str(fpath)})
            _mark_processed(db, item, "approved", details=trace_details)
            stats.ideas.append(
                {
                    "idea_id": idea_id,
                    "title": idea_title,
                    "score": cr.score,
                    "path": str(fpath),
                }
            )
        except Exception as exc:
            stats.errors += 1
            error_excerpt = traceback.format_exc()[-500:]
            _mark_processed(
                db,
                item,
                "error",
                details={
                    **trace_details,
                    "error": str(exc),
                    "traceback_excerpt": error_excerpt,
                },
            )
            prog(f"错误 topic {item.id}: {error_excerpt}")

    return stats


def run_pipeline(
    *,
    source: str,
    mode: str = "daily_report",
    max_items: Optional[int] = None,
    keywords: Optional[list[str]] = None,
    settings: Optional[Settings] = None,
    db: Optional[SqliteManager] = None,
    output_dir: str | Path = "",
    on_progress: Optional[OnProgress] = None,
) -> RunStats:
    settings = settings or get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY 未配置，请在 .env 中设置")

    output_dir = output_dir or settings.output_dir
    db = db or SqliteManager(settings.ideahunter_sqlite_path)
    scraper = get_scraper(source)
    try:
        items = scraper.fetch_raw_items(max_items=max_items)
    finally:
        scraper.close()

    stats = _process_items(
        items,
        settings=settings,
        db=db,
        output_dir=output_dir,
        keywords=keywords,
        on_progress=on_progress,
        progress_prefix="分析",
    )
    if mode == "daily_report":
        if on_progress:
            on_progress("daily_report 完成")
    return stats


def run_ingested_contents(
    *,
    source_name: str,
    content_list: list[str],
    settings: Optional[Settings] = None,
    db: Optional[SqliteManager] = None,
    output_dir: str | Path = "",
    on_progress: Optional[OnProgress] = None,
) -> RunStats:
    """将外部文本列表包装为 RawItem 并走同一流水线（webhook）。"""
    settings = settings or get_settings()
    output_dir = output_dir or settings.output_dir
    db = db or SqliteManager(settings.ideahunter_sqlite_path)
    items = [
        _build_ingest_item(source_name, idx, text)
        for idx, text in enumerate(content_list)
    ]
    return _process_items(
        items,
        settings=settings,
        db=db,
        output_dir=output_dir,
        on_progress=on_progress,
        progress_prefix="ingest",
    )
