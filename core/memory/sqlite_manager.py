from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class IdeaRecord:
    idea_id: str
    title: str
    score: int
    source: str
    markdown_prd: str
    tech_stack: list[str]
    target_audience: str
    raw_complaints_analyzed: int
    created_at: str
    external_ref: str = ""


@dataclass
class ProcessedItemRecord:
    source: str
    external_id: str
    outcome: str
    title: str
    url: str
    details: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class SqliteManager:
    def __init__(self, db_path: str) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS processed_items (
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (source, external_id)
            );

            CREATE TABLE IF NOT EXISTS ideas (
                idea_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                score INTEGER NOT NULL,
                source TEXT NOT NULL,
                markdown_prd TEXT NOT NULL,
                tech_stack TEXT NOT NULL,
                target_audience TEXT NOT NULL,
                raw_complaints_analyzed INTEGER NOT NULL DEFAULT 1,
                external_ref TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                progress TEXT NOT NULL DEFAULT '',
                result_count INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        self._ensure_processed_items_columns()
        self._conn.commit()

    def _ensure_processed_items_columns(self) -> None:
        columns = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(processed_items)").fetchall()
        }
        wanted = {
            "title": "TEXT NOT NULL DEFAULT ''",
            "url": "TEXT NOT NULL DEFAULT ''",
            "details": "TEXT NOT NULL DEFAULT '{}'",
            "updated_at": "TEXT NOT NULL DEFAULT ''",
        }
        for name, ddl in wanted.items():
            if name in columns:
                continue
            self._conn.execute(f"ALTER TABLE processed_items ADD COLUMN {name} {ddl}")

    def is_processed(self, source: str, external_id: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM processed_items WHERE source = ? AND external_id = ?",
            (source, external_id),
        )
        return cur.fetchone() is not None

    def mark_processed(
        self,
        source: str,
        external_id: str,
        outcome: str,
        *,
        title: str = "",
        url: str = "",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        now = _utc_now_iso()
        payload = json.dumps(details or {}, ensure_ascii=False)
        self._conn.execute(
            """
            INSERT INTO processed_items (
                source, external_id, outcome, title, url, details, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, external_id) DO UPDATE SET
                outcome = excluded.outcome,
                title = excluded.title,
                url = excluded.url,
                details = excluded.details,
                updated_at = excluded.updated_at
            """,
            (source, external_id, outcome, title, url, payload, now, now),
        )
        self._conn.commit()

    def insert_idea(
        self,
        *,
        title: str,
        score: int,
        source: str,
        markdown_prd: str,
        tech_stack: list[str],
        target_audience: str,
        raw_complaints_analyzed: int = 1,
        external_ref: str = "",
        idea_id: Optional[str] = None,
    ) -> str:
        iid = idea_id or f"ida_{uuid.uuid4().hex[:12]}"
        self._conn.execute(
            """
            INSERT INTO ideas (
                idea_id, title, score, source, markdown_prd, tech_stack,
                target_audience, raw_complaints_analyzed, external_ref, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                iid,
                title,
                score,
                source,
                markdown_prd,
                json.dumps(tech_stack, ensure_ascii=False),
                target_audience,
                raw_complaints_analyzed,
                external_ref,
                _utc_now_iso(),
            ),
        )
        self._conn.commit()
        return iid

    def get_idea(self, idea_id: str) -> Optional[IdeaRecord]:
        cur = self._conn.execute("SELECT * FROM ideas WHERE idea_id = ?", (idea_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_idea(row)

    def list_ideas(
        self,
        *,
        min_score: int = 0,
        source: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[int, list[IdeaRecord]]:
        page = max(1, page)
        size = max(1, min(100, size))
        offset = (page - 1) * size
        where: list[str] = ["score >= ?"]
        params: list[Any] = [min_score]
        if source:
            where.append("source = ?")
            params.append(source)
        if search:
            where.append("(title LIKE ? OR markdown_prd LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        wh = " AND ".join(where)
        cur = self._conn.execute(f"SELECT COUNT(*) FROM ideas WHERE {wh}", params)
        total = int(cur.fetchone()[0])
        cur = self._conn.execute(
            f"SELECT * FROM ideas WHERE {wh} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [*params, size, offset],
        )
        items = [self._row_to_idea(r) for r in cur.fetchall()]
        return total, items

    def _row_to_idea(self, row: sqlite3.Row) -> IdeaRecord:
        tech = json.loads(row["tech_stack"] or "[]")
        if not isinstance(tech, list):
            tech = []
        return IdeaRecord(
            idea_id=row["idea_id"],
            title=row["title"],
            score=int(row["score"]),
            source=row["source"],
            markdown_prd=row["markdown_prd"],
            tech_stack=[str(x) for x in tech],
            target_audience=row["target_audience"] or "",
            raw_complaints_analyzed=int(row["raw_complaints_analyzed"] or 1),
            created_at=row["created_at"],
            external_ref=row["external_ref"] or "",
        )

    def list_processed_items(
        self,
        *,
        source: Optional[str] = None,
        outcome: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[int, list[ProcessedItemRecord]]:
        page = max(1, page)
        size = max(1, min(100, size))
        offset = (page - 1) * size
        where: list[str] = ["1 = 1"]
        params: list[Any] = []
        if source:
            where.append("source = ?")
            params.append(source)
        if outcome:
            where.append("outcome = ?")
            params.append(outcome)
        where_sql = " AND ".join(where)
        total = int(
            self._conn.execute(
                f"SELECT COUNT(*) FROM processed_items WHERE {where_sql}",
                params,
            ).fetchone()[0]
        )
        rows = self._conn.execute(
            f"""
            SELECT * FROM processed_items
            WHERE {where_sql}
            ORDER BY updated_at DESC, created_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, size, offset],
        ).fetchall()
        return total, [self._row_to_processed_item(row) for row in rows]

    def _row_to_processed_item(self, row: sqlite3.Row) -> ProcessedItemRecord:
        try:
            details = json.loads(row["details"] or "{}")
        except json.JSONDecodeError:
            details = {}
        if not isinstance(details, dict):
            details = {}
        return ProcessedItemRecord(
            source=row["source"],
            external_id=row["external_id"],
            outcome=row["outcome"],
            title=row["title"] or "",
            url=row["url"] or "",
            details=details,
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or row["created_at"] or "",
        )

    def create_task(self, task_id: str) -> None:
        now = _utc_now_iso()
        self._conn.execute(
            """
            INSERT INTO tasks (task_id, status, progress, result_count, error, created_at, updated_at)
            VALUES (?, 'pending', '', 0, NULL, ?, ?)
            """,
            (task_id, now, now),
        )
        self._conn.commit()

    def update_task(
        self,
        task_id: str,
        *,
        status: Optional[str] = None,
        progress: Optional[str] = None,
        result_count: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        row = self._conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
        ).fetchone()
        if row is None:
            return
        st = status if status is not None else row["status"]
        pr = progress if progress is not None else row["progress"]
        rc = result_count if result_count is not None else row["result_count"]
        err = error if error is not None else row["error"]
        self._conn.execute(
            """
            UPDATE tasks SET status = ?, progress = ?, result_count = ?, error = ?, updated_at = ?
            WHERE task_id = ?
            """,
            (st, pr, rc, err, _utc_now_iso(), task_id),
        )
        self._conn.commit()

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        cur = self._conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "task_id": row["task_id"],
            "status": row["status"],
            "progress": row["progress"] or "",
            "result_count": int(row["result_count"] or 0),
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
