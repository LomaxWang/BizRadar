from __future__ import annotations

import logging
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.settings import Settings, get_settings
from core.logging_config import setup_logging
from core.memory.sqlite_manager import SqliteManager
from core.orchestrator import run_ingested_contents, run_pipeline
from core.scheduler import start_scheduler

logger = logging.getLogger(__name__)

_scheduler = None  # will hold BackgroundScheduler when schedule_enabled

API_PREFIX = "/api/v1"


def ok(data: Any = None, msg: str = "success", code: int = 200) -> dict[str, Any]:
    return {"code": code, "msg": msg, "data": data}


def require_auth(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[Optional[str], Header()] = None,
) -> None:
    key = (settings.ideahunter_api_key or "").strip()
    if not key:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": 40101, "msg": "Unauthorized"})
    token = authorization[7:].strip()
    if token != key:
        raise HTTPException(status_code=401, detail={"code": 40101, "msg": "Unauthorized"})


def get_db(settings: Annotated[Settings, Depends(get_settings)]) -> Iterator[SqliteManager]:
    db = SqliteManager(settings.ideahunter_sqlite_path)
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="IdeaHunter API", version="0.1.0")


class ScanBody(BaseModel):
    source: str = Field(..., description="数据源插件名，如 v2ex")
    keywords: Optional[list[str]] = None
    max_items: Optional[int] = Field(default=None, ge=1, le=500)


class IngestBody(BaseModel):
    source_name: str
    content_list: list[str] = Field(..., min_length=1, max_length=100)


@app.on_event("startup")
def _startup() -> None:
    global _scheduler
    setup_logging()
    settings = get_settings()
    if settings.schedule_enabled:
        _scheduler = start_scheduler(settings)
        logger.info("Background scheduler started")


@app.on_event("shutdown")
def _shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
        _scheduler = None


@app.post(f"{API_PREFIX}/tasks/scan")
def post_scan(
    body: ScanBody,
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(require_auth)],
    db: Annotated[SqliteManager, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    # 提前校验数据源，避免后台任务才报错
    from core.orchestrator import get_scraper
    try:
        get_scraper(body.source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": 40001, "msg": str(e)})

    task_id = f"tsk_{uuid.uuid4().hex[:16]}"
    db.create_task(task_id)

    def job() -> None:
        ldb = SqliteManager(settings.ideahunter_sqlite_path)
        try:
            ldb.update_task(
                task_id,
                status="processing",
                progress="Starting scan…",
                result_count=0,
            )

            def prog(m: str) -> None:
                ldb.update_task(task_id, progress=m)

            stats = run_pipeline(
                source=body.source,
                mode="daily_report",
                max_items=body.max_items,
                keywords=body.keywords,
                settings=settings,
                db=ldb,
                output_dir=settings.output_dir,
                on_progress=prog,
            )
            ldb.update_task(
                task_id,
                status="completed",
                progress="completed",
                result_count=stats.approved,
            )
        except Exception as e:
            ldb = SqliteManager(settings.ideahunter_sqlite_path)
            ldb.update_task(
                task_id,
                status="failed",
                progress="failed",
                error=str(e)[:2000],
            )

    background_tasks.add_task(job)
    return ok({"task_id": task_id, "status": "pending"}, msg="Task created successfully")


@app.post(f"{API_PREFIX}/webhooks/ingest")
def post_ingest(
    body: IngestBody,
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(require_auth)],
    db: Annotated[SqliteManager, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    task_id = f"tsk_{uuid.uuid4().hex[:16]}"
    db.create_task(task_id)

    def job() -> None:
        ldb = SqliteManager(settings.ideahunter_sqlite_path)
        try:
            ldb.update_task(task_id, status="processing", progress="Ingesting…")
            stats = run_ingested_contents(
                source_name=body.source_name,
                content_list=body.content_list,
                settings=settings,
                db=ldb,
                output_dir=settings.output_dir,
                on_progress=lambda m: ldb.update_task(task_id, progress=m),
            )
            ldb.update_task(
                task_id,
                status="completed",
                progress="completed",
                result_count=stats.approved,
            )
        except Exception as e:
            ldb = SqliteManager(settings.ideahunter_sqlite_path)
            ldb.update_task(
                task_id,
                status="failed",
                progress="failed",
                error=str(e)[:2000],
            )

    background_tasks.add_task(job)
    return ok({"task_id": task_id, "status": "pending"}, msg="Task created successfully")


@app.get(f"{API_PREFIX}/tasks/{{task_id}}")
def get_task(
    task_id: str,
    _: Annotated[None, Depends(require_auth)],
    db: Annotated[SqliteManager, Depends(get_db)],
) -> dict[str, Any]:
    row = db.get_task(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"code": 40401, "msg": "Not Found"})
    return ok(
        {
            "task_id": row["task_id"],
            "status": row["status"],
            "progress": row["progress"],
            "result_count": row["result_count"],
            "error": row["error"],
        }
    )


@app.get(f"{API_PREFIX}/ideas")
def list_ideas(
    _: Annotated[None, Depends(require_auth)],
    db: Annotated[SqliteManager, Depends(get_db)],
    min_score: int = Query(default=0, ge=0, le=100),
    source: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    total, items = db.list_ideas(min_score=min_score, source=source, page=page, size=size)
    return ok(
        {
            "total": total,
            "items": [
                {
                    "idea_id": it.idea_id,
                    "title": it.title,
                    "score": it.score,
                    "source": it.source,
                    "created_at": it.created_at,
                }
                for it in items
            ],
        }
    )


@app.get(f"{API_PREFIX}/ideas/{{idea_id}}")
def get_idea(
    idea_id: str,
    _: Annotated[None, Depends(require_auth)],
    db: Annotated[SqliteManager, Depends(get_db)],
) -> dict[str, Any]:
    it = db.get_idea(idea_id)
    if it is None:
        raise HTTPException(status_code=404, detail={"code": 40401, "msg": "Not Found"})
    return ok(
        {
            "idea_id": it.idea_id,
            "title": it.title,
            "score": it.score,
            "raw_complaints_analyzed": it.raw_complaints_analyzed,
            "markdown_prd": it.markdown_prd,
            "tech_stack": it.tech_stack,
            "target_audience": it.target_audience,
        }
    )


@app.get(f"{API_PREFIX}/processed-items")
def list_processed_items(
    _: Annotated[None, Depends(require_auth)],
    db: Annotated[SqliteManager, Depends(get_db)],
    source: Optional[str] = None,
    outcome: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    total, items = db.list_processed_items(
        source=source,
        outcome=outcome,
        page=page,
        size=size,
    )
    return ok(
        {
            "total": total,
            "items": [
                {
                    "source": it.source,
                    "external_id": it.external_id,
                    "outcome": it.outcome,
                    "title": it.title,
                    "url": it.url,
                    "details": it.details,
                    "created_at": it.created_at,
                    "updated_at": it.updated_at,
                }
                for it in items
            ],
        }
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
