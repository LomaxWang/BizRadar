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
    """数据源插件基类。

    子类可在 __init__ 中调用 super().__init__(multi_hop=..., max_comments=...)
    以启用多跳采集能力（获取评论/正文详情）。
    """

    name: str = "base"

    def __init__(
        self,
        *,
        multi_hop: bool = False,
        max_comments: int = 3,
    ) -> None:
        self.multi_hop = multi_hop
        self.max_comments = max_comments

    @abstractmethod
    def fetch_raw_items(
        self,
        *,
        max_items: Optional[int] = None,
        search_keywords: Optional[list[str]] = None,
    ) -> list[RawItem]:
        """拉取一批原始条目。

        Args:
            max_items: 最多返回条目数，None 表示插件默认行为。
            search_keywords: 本轮搜索关键词列表，None 表示使用插件默认查询。
        """

    def close(self) -> None:
        """释放资源。子类可覆盖。"""

    def __enter__(self) -> "BaseScraper":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
