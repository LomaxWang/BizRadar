from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class RawItem(BaseModel):
    """统一采集输出，供编排层与 Agent 使用。"""

    id: str = Field(description="来源侧唯一 ID，如 V2EX topic id")
    url: str = ""
    title: str = ""
    body: str = Field(default="", description="正文或摘要")
    source: str = Field(default="", description="插件名，如 v2ex")
    extra: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class BaseScraper(ABC):
    """数据源插件基类。"""

    name: str = "base"

    @abstractmethod
    def fetch_raw_items(self, *, max_items: Optional[int] = None) -> list[RawItem]:
        """拉取一批原始条目；max_items 为上限，None 表示插件默认行为。"""

    def close(self) -> None:
        """释放资源。子类可覆盖。"""

    def __enter__(self) -> "BaseScraper":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
