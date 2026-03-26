"""Tests for core.memory.sqlite_manager.SqliteManager."""

from __future__ import annotations

import pytest

from core.memory.sqlite_manager import SqliteManager


@pytest.fixture()
def db(tmp_path):
    """Create an in-memory SqliteManager for each test."""
    # Use a file-based DB in tmp_path so that SqliteManager.__init__
    # can create parent dirs without issues, but it's still isolated.
    mgr = SqliteManager(str(tmp_path / "test.db"))
    yield mgr
    mgr.close()


# ---------- mark_processed / is_processed ----------


class TestProcessedItems:
    def test_is_processed_false_initially(self, db: SqliteManager):
        assert db.is_processed("v2ex", "123") is False

    def test_mark_then_is_processed(self, db: SqliteManager):
        db.mark_processed("v2ex", "123", "approved")
        assert db.is_processed("v2ex", "123") is True

    def test_mark_processed_upsert(self, db: SqliteManager):
        """Marking the same (source, external_id) twice should update, not fail."""
        db.mark_processed("v2ex", "123", "dropped")
        db.mark_processed("v2ex", "123", "approved", title="updated")
        assert db.is_processed("v2ex", "123") is True
        # Verify the update took effect via list_processed_items
        total, items = db.list_processed_items(source="v2ex")
        assert total == 1
        assert items[0].outcome == "approved"
        assert items[0].title == "updated"

    def test_mark_processed_with_details(self, db: SqliteManager):
        db.mark_processed(
            "v2ex", "456", "rejected",
            title="Test Title",
            url="https://example.com",
            details={"score": 42},
        )
        total, items = db.list_processed_items(source="v2ex")
        assert total == 1
        assert items[0].details == {"score": 42}
        assert items[0].url == "https://example.com"

    def test_different_sources_independent(self, db: SqliteManager):
        db.mark_processed("v2ex", "100", "approved")
        db.mark_processed("reddit", "100", "rejected")
        assert db.is_processed("v2ex", "100") is True
        assert db.is_processed("reddit", "100") is True
        assert db.is_processed("twitter", "100") is False


# ---------- insert_idea / list_ideas ----------


class TestIdeas:
    def _insert_idea(self, db: SqliteManager, *, title: str = "Test", score: int = 80, **kw):
        defaults = dict(
            title=title,
            score=score,
            source="v2ex",
            markdown_prd="# PRD",
            tech_stack=["Python", "FastAPI"],
            target_audience="developers",
        )
        defaults.update(kw)
        return db.insert_idea(**defaults)

    def test_insert_and_get(self, db: SqliteManager):
        idea_id = self._insert_idea(db)
        assert idea_id.startswith("ida_")
        idea = db.get_idea(idea_id)
        assert idea is not None
        assert idea.title == "Test"
        assert idea.score == 80
        assert idea.tech_stack == ["Python", "FastAPI"]

    def test_insert_with_custom_id(self, db: SqliteManager):
        idea_id = self._insert_idea(db, idea_id="custom_001")
        assert idea_id == "custom_001"

    def test_get_nonexistent(self, db: SqliteManager):
        assert db.get_idea("no_such_id") is None

    def test_list_empty(self, db: SqliteManager):
        total, items = db.list_ideas()
        assert total == 0
        assert items == []

    def test_list_pagination(self, db: SqliteManager):
        for i in range(5):
            self._insert_idea(db, title=f"Idea {i}", score=50 + i)
        total, page1 = db.list_ideas(page=1, size=2)
        assert total == 5
        assert len(page1) == 2
        total, page3 = db.list_ideas(page=3, size=2)
        assert total == 5
        assert len(page3) == 1  # 5th item

    def test_list_min_score_filter(self, db: SqliteManager):
        self._insert_idea(db, title="low", score=30)
        self._insert_idea(db, title="high", score=90)
        total, items = db.list_ideas(min_score=80)
        assert total == 1
        assert items[0].title == "high"

    def test_list_source_filter(self, db: SqliteManager):
        self._insert_idea(db, title="v2ex idea", source="v2ex")
        self._insert_idea(db, title="reddit idea", source="reddit")
        total, items = db.list_ideas(source="reddit")
        assert total == 1
        assert items[0].source == "reddit"


# ---------- create_task / update_task / get_task ----------


class TestTasks:
    def test_create_and_get(self, db: SqliteManager):
        db.create_task("tsk_001")
        task = db.get_task("tsk_001")
        assert task is not None
        assert task["task_id"] == "tsk_001"
        assert task["status"] == "pending"
        assert task["result_count"] == 0
        assert task["error"] is None

    def test_get_nonexistent(self, db: SqliteManager):
        assert db.get_task("no_such_task") is None

    def test_update_status(self, db: SqliteManager):
        db.create_task("tsk_002")
        db.update_task("tsk_002", status="processing", progress="50%")
        task = db.get_task("tsk_002")
        assert task["status"] == "processing"
        assert task["progress"] == "50%"

    def test_update_result_count(self, db: SqliteManager):
        db.create_task("tsk_003")
        db.update_task("tsk_003", status="completed", result_count=5)
        task = db.get_task("tsk_003")
        assert task["result_count"] == 5

    def test_update_error(self, db: SqliteManager):
        db.create_task("tsk_004")
        db.update_task("tsk_004", status="failed", error="boom")
        task = db.get_task("tsk_004")
        assert task["status"] == "failed"
        assert task["error"] == "boom"

    def test_update_nonexistent_is_noop(self, db: SqliteManager):
        # Should not raise
        db.update_task("nonexistent", status="failed")

    def test_partial_update_preserves_fields(self, db: SqliteManager):
        db.create_task("tsk_005")
        db.update_task("tsk_005", status="processing")
        db.update_task("tsk_005", progress="75%")
        task = db.get_task("tsk_005")
        assert task["status"] == "processing"  # preserved
        assert task["progress"] == "75%"  # updated
